import enum


class JiraFieldKeys(enum.Enum):
    ID = "id"
    KEY = "key"
    NAME = "name"
    UNTRANSLATEDNAME = "untranslatedName"
    CUSTOM = "custom"
    ORDERABLE = "orderable"
    NAVIGABLE = "navigable"
    SEARCHABLE = "searchable"
    CLAUSENAMES = "clauseNames"
    SCHEMA = "schema"


class JiraFieldType(enum.Enum):
    ANY = "any"
    ARRAY = "array"
    COMMENTS_PAGE = "comments-page"
    DATE = "date"
    DATETIME = "datetime"
    ISSUERESTRICTION = "issuerestriction"
    ISSUETYPE = "issuetype"
    NUMBER = "number"
    OPTION = "option"
    OPTION_WITH_CHILD = "option-with-child"
    OPTION2 = "option2"
    PRIORITY = "priority"
    PROGRESS = "progress"
    PROJECT = "project"
    RESOLUTION = "resolution"
    SD_APPROVALS = "sd-approvals"
    SD_CUSTOMERREQUESTTYPE = "sd-customerrequesttype"
    SD_FEEDBACK = "sd-feedback"
    SD_REQUEST_LANG = "sd-request-lang"
    SD_SERVICELEVELAGREEMENT = "sd-servicelevelagreement"
    SECURITYLEVEL = "securitylevel"
    STATUS = "status"
    STRING = "string"
    TIMETRACKING = "timetracking"
    USER = "user"
    VOTES = "votes"
    WATCHES = "watches"


class ListSprintSprintOption(enum.Enum):
    OPEN = "open"
    FUTURE = "future"
    CLOSED = "closed"
