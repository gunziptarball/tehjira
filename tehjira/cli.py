#!python
import datetime
import json
import logging
import pathlib
import sys
import typing as t

import pendulum
import sqlalchemy as sa
import tabulate as tabulate
import typer
from jira import JIRA, Issue
from jira.client import ResultList
from sqlalchemy import orm

import tehjira.schemas
from tehjira.models import JiraBase, JiraIssue

settings = tehjira.schemas.Settings()

ATLASSIAN_URL = settings.jira.url
ATLASSIAN_API_TOKEN = settings.jira.token
ATLASSIAN_EMAIL = settings.jira.email
TEHJIRA_DB_URL = settings.db_url

app = typer.Typer()
_fields: t.Dict[str, str] = {}

fields_path = pathlib.Path(".fields.json")

PATH_TO_SQL_VIEWS = pathlib.Path(__file__).parent / "data/sql/vw_issues.sql"

LARGE_RESULT_THRESHOLD = 100

fields_of_interest = ["Summary", "Status", "Sprint", "Issue Type", "Story Points"]

logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


def create_jira():
    return JIRA(
        ATLASSIAN_URL,
        basic_auth=(ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN),
    )


jira_engine = sa.create_engine(TEHJIRA_DB_URL)
JiraSessionLocal = orm.sessionmaker(autocommit=False, autoflush=False, bind=jira_engine)


def initialize_db(echo: bool = False):
    with jira_engine.connect() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS jira")
    m: sa.MetaData = JiraBase.metadata
    m.create_all(
        bind=jira_engine,
        tables=(JiraIssue.__table__,),
        checkfirst=True,
    )
    assert PATH_TO_SQL_VIEWS.exists(), f"cannot find view sql at {PATH_TO_SQL_VIEWS}"
    with jira_engine.connect() as conn:
        conn.execute(PATH_TO_SQL_VIEWS.read_text())


def sync_status(sess: orm.Session) -> t.Optional[datetime.datetime]:
    with sess.bind.connect() as conn:
        return conn.scalar(sa.select(sa.func.max(JiraIssue.watermark)))


class LargeResultWarning(Warning):
    def __init__(self, jql: str, result: ResultList[Issue]):
        self.jql: str = jql
        self.result_size: int = result.total
        super().__init__()

    def __str__(self):
        return f"Large Result: {self.result_size} from JQL: {self.jql}"


def sync_and_yield_from_jql(
    sess: orm.Session, jql: str, *, allow_large_result: bool = False
) -> t.Iterable[JiraIssue]:
    logger.info(validate_jql(jql))
    for issues in iter_results(validate_jql(jql), fields="*all"):
        if issues.total > LARGE_RESULT_THRESHOLD and not allow_large_result:
            raise LargeResultWarning(jql, issues)
        for issue in issues:
            logger.info(f"Syncing {issue.key} - {issue.get_field('summary')}")
            ji = sess.query(JiraIssue).get(issue.key)
            issue_updated = issue.get_field("updated")
            if ji is None:
                ji = JiraIssue(issue_key=issue.key)
            else:
                if ji.raw["fields"]["updated"] == issue_updated:  # type: ignore
                    continue
            ji.watermark = issue_updated
            ji.raw = issue.raw
            sess.add(ji)
            sess.commit()
            yield ji


def sync_and_yield(
    sess: orm.Session, watermark: datetime.datetime, *, allow_large_result: bool = False
) -> t.Iterable[JiraIssue]:
    watermark_et = watermark.astimezone(pendulum.timezone(settings.local_timezone))
    jql = validate_jql(f'updated >= "{watermark_et.strftime("%Y/%m/%d %H:%M")}"')
    yield from sync_and_yield_from_jql(sess, jql, allow_large_result=allow_large_result)


def validate_jql(jql: str) -> str:
    assert jql, "Empty query!"

    parts = jql.split(" ORDER BY ")
    if len(parts) == 1:
        parts.append("key")
    else:
        if "key" not in parts[1]:
            parts[1] += ", key"
    assert len(parts) == 2
    return " ORDER BY ".join(parts)


def iter_results(
    jql: str, max_results: int = 50, fields: t.Union[str, t.List[str]] = "*all"
) -> t.Iterator[ResultList[Issue]]:
    jql = validate_jql(jql)

    result_count = -1
    total_result_count = 0
    while result_count != 0:
        result = create_jira().search_issues(
            jql,
            maxResults=max_results,
            startAt=total_result_count,
            fields=fields,
        )
        result_count = len(result)
        total_result_count += result_count
        yield result


def fetch_fields() -> t.Dict[str, str]:
    if _fields:
        return _fields
    if fields_path.exists():
        _fields.update(json.loads(fields_path.read_text()))
        return _fields
    _fields.update({f["name"]: f["id"] for f in create_jira().fields()})
    fields_path.write_text(json.dumps(_fields, indent=2))
    return _fields


@app.command("sync")
def _sync(jql: str = None, *, force: bool = False):
    initialize_db()
    try:
        if jql is None:
            a_year_ago = pendulum.DateTime.now() - datetime.timedelta(days=360)
            with JiraSessionLocal() as sess:  # type: orm.Session
                watermark = sync_status(sess)

            if watermark is None:
                if not typer.confirm(
                    "DB has not been synchronized. Seed with project? (this could take a while)"
                ):
                    return
                watermark = a_year_ago
            with JiraSessionLocal() as sess:
                synced_issues = sync_and_yield(
                    sess,
                    watermark - datetime.timedelta(minutes=1),
                    allow_large_result=force,
                )
                for synced in synced_issues:
                    typer.echo(typer.style(f"Updated: [{synced}] {synced.summary}"))
        else:
            with JiraSessionLocal() as sess:
                for synced in sync_and_yield_from_jql(
                    sess, jql, allow_large_result=force
                ):
                    typer.echo(typer.style(f"Updated from JQL {synced}"))
        with JiraSessionLocal() as sess:
            ss = sync_status(sess)
            if ss is None:
                return
            typer.echo(f"Last synchronized {ss.isoformat()}")
    except LargeResultWarning as lrw:
        if not typer.confirm(str(lrw) + " Continue anyway?"):
            raise typer.Abort()
        return _sync(jql, force=True)


@app.command()
def show_fields():
    """Display JIRA fields"""
    fields = create_jira().fields()
    keys = ("id", "key", "name", "custom", "orderable", "navigable", "searchable")
    result = [[f[k] for k in keys] for f in fields][:20]
    typer.echo(tabulate.tabulate(result, headers=keys))


@app.command()
def backup(path: pathlib.Path = None):
    """
    Dump issue data from db into JSON lines

    """
    with jira_engine.connect() as conn:
        with path.open("w") if path else sys.stdout as f:
            for row in conn.execute(sa.select([JiraIssue.raw])):
                json.dump(row.raw, f)
                f.write("\n")


if __name__ == "__main__":
    app()
