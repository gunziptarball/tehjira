import copy
import typing as t

import sqlalchemy as sa
from jira import Issue
from sqlalchemy import orm
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

JiraBase = declarative_base()


class JiraIssueLink(JiraBase):
    __tablename__ = "vw_issue_links"
    __table_args__ = {"schema": "jira"}

    issue_key = sa.Column(
        "issue_key",
        sa.String(30),
        sa.ForeignKey("jira.jira_issue.issue_key"),
        primary_key=True,
    )
    linked_issue_key = sa.Column(
        sa.String(30), sa.ForeignKey("jira.jira_issue.issue_key"), primary_key=True
    )
    link_type = sa.Column("link_type", sa.String(50), nullable=False, primary_key=True)

    parent_issue = orm.relationship(
        "JiraIssue", uselist=False, foreign_keys=[issue_key], viewonly=True
    )
    linked_issue = orm.relationship(
        "JiraIssue", uselist=False, foreign_keys=[linked_issue_key], viewonly=True
    )

    def __repr__(self) -> str:
        return f"<JiraIssueLink(from='{self.issue_key}', type='{self.link_type}', to='{self.linked_issue_key}"

    def __str__(self):
        return " ".join((self.issue_key, self.link_type, self.linked_issue_key))


class JiraIssue(JiraBase):
    __tablename__ = "jira_issue"
    __table_args__ = {"schema": "jira"}

    issue_key = sa.Column("issue_key", sa.String(30), primary_key=True)
    watermark = sa.Column("watermark", sa.DateTime(timezone=True), nullable=False)
    raw = sa.Column("raw", JSONB, nullable=False)

    # https://docs.sqlalchemy.org/en/14/orm/join_conditions.html#self-referential-many-to-many-relationship
    linked_issues = orm.relationship(
        "JiraIssue",
        secondary=JiraIssueLink.__table__,
        primaryjoin=issue_key == JiraIssueLink.issue_key,
        secondaryjoin=issue_key == JiraIssueLink.linked_issue_key,
        backref="linking_issues",
        viewonly=True,
    )  # type: t.Iterable[JiraIssue]

    outward_issue_links = orm.relationship(
        JiraIssueLink, primaryjoin=issue_key == JiraIssueLink.issue_key, viewonly=True
    )  # type: t.Iterable[JiraIssueLink]

    _ix_watermark = sa.Index("ix_watermark")

    @classmethod
    def from_issue(cls, issue: Issue) -> "JiraIssue":
        return cls(
            issue_key=issue.key, watermark=issue.get_field("updated"), raw=issue.raw
        )

    @property
    def _fields(self):
        return copy.deepcopy(self.raw.get("fields"))

    @property
    def _summary(self):
        return self._fields and self._fields.get("summary")

    def __str__(self) -> str:
        return str(self.issue_key)

    def __repr__(self) -> str:
        return f"<JiraIssue(key='{self.issue_key}', summary='{self._summary}'>"

    # TODO: I'll bet there's a clever way to create a custom property type
    #   to do this for other JSON fields
    @hybrid_property  # type: ignore
    def summary(self) -> str:
        return self.raw["fields"]["summary"]

    @summary.setter  # type: ignore
    def summary(self, value: str):
        raw = copy.deepcopy(self.raw)
        raw["fields"]["summary"] = value
        self.raw = raw

    # noinspection PyMethodParameters
    @summary.expression  # type: ignore
    def summary(cls: t.Type["JiraIssue"]):  # type: ignore
        return cls.raw["fields"]["summary"].astext
