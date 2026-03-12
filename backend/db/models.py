import uuid
from datetime import datetime, timezone
from enum import Enum
from sqlalchemy.sql import text
from sqlalchemy import (ARRAY, FLOAT, JSON, Boolean, Column, DateTime,
                        ForeignKey, Index, Integer, Numeric, String, Text,
                        UniqueConstraint, Sequence, desc)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import backref, declarative_base, relationship
from sqlalchemy.sql import func

from config import MAX_CONCURRENT_TASKS_DEFAULT

Base = declarative_base(cls=AsyncAttrs)


class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    user_email = Column(String, nullable=True)
    user_username = Column(String, nullable=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    method = Column(String, nullable=False)
    endpoint_path = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    user_params = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)

    __table_args__ = (
        Index('ix_log_entries_workspace_id', 'workspace_id'),
        Index('ix_log_entries_timestamp', 'timestamp'),
        Index('ix_log_entries_workspace_id_user_id', 'workspace_id', 'user_id'),
    )


class Workspace(Base):
    __tablename__ = "workspaces"

    workspace_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    tariff_id = Column(UUID(as_uuid=True), ForeignKey("tariffs.tariff_id"), nullable=True)
    tariff_expiration = Column(DateTime(timezone=True), nullable=True)
    tariff_start_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    status = Column(String, nullable=False, default="Active")
    max_concurrent_tasks = Column(Integer, default=MAX_CONCURRENT_TASKS_DEFAULT)

    # users = relationship("User", back_populates="workspaces")
    # memberships = relationship("WorkspaceMembership", back_populates="workspace")


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.workspace_id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=False)
    avatar = Column(JSON, default=dict, nullable=True)
    role = Column(String, ForeignKey("roles.role"), nullable=False)
    role_title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Invited")  # "Invited" или "Active"
    invitation_link = Column(String, nullable=True)
    last_action_date = Column(DateTime(timezone=True), nullable=True)

    # projects = relationship("ProjectUser", back_populates="user_id")
    # workspace = relationship("Workspace", back_populates="memberships")
    # user = relationship("User", back_populates="memberships")
    __table_args__ = (
        Index('idx_workspace_membership_workspace_id', 'workspace_id'),
        Index('idx_workspace_membership_last_action_date', 'last_action_date'),
        Index('idx_workspace_membership_composite', 'workspace_id', 'role', 'status'),
    )


class Usage(Base):
    __tablename__ = "workspace_usage"
    usage_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.workspace_id"), nullable=False)
    feature_name = Column(String, nullable=False)
    usage_count = Column(Integer, default=0)
    last_reset = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (
        Index('idx_workspace_usage_workspace_id', 'workspace_id'),
        Index('idx_workspace_usage_last_reset', 'last_reset'),
        Index('idx_workspace_usage_workspace_id_feature_name', 'workspace_id', 'feature_name'),
    )


class ProjectUser(Base):
    __tablename__ = "project_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.project_id"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.workspace_id'))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    role = Column(String, ForeignKey("roles.role"), nullable=False)  # "Admin", "Member", "Read-Only"

    __table_args__ = (
        Index('idx_project_users_project_id', 'project_id'),
        Index('idx_project_users_workspace_user', 'workspace_id', 'user_id'),
        Index('idx_project_user_user_workspace', 'user_id', 'workspace_id'),
        Index('idx_project_users_project_id_workspace_user', 'project_id', 'workspace_id', 'user_id'),
    )

    # project = relationship("Project", back_populates="project_users")
    # user = relationship("User", back_populates="project_users")


class Tariffs(Base):
    __tablename__ = "tariffs"

    tariff_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tariff_name = Column(String, nullable=False, unique=True)
    tariff_full_name = Column(String, nullable=True)
    description = Column(String, nullable=True)
    tariff_limits = relationship('TariffLimits', back_populates='tariff', cascade='all, delete-orphan', lazy='select')
    cnt_months = Column(Integer, nullable=False)
    discount = Column(Integer, nullable=True)
    price = Column(Numeric(scale=2), nullable=False)
    cur = Column(String, nullable=True)
    period = Column(String, nullable=True)
    buy_tariff_manual_only = Column(Boolean(), default=False)
    best_value = Column(Boolean(), default=False)
    can_buy_streams = Column(Boolean(), default=True)
    visible = Column(Boolean(), default=True)


class TariffLimits(Base):
    __tablename__ = "tariff_limits"
    limit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tariff_id = Column(UUID(as_uuid=True), ForeignKey("tariffs.tariff_id"), nullable=False)
    feature_name = Column(String, nullable=False)
    feature_full_name = Column(String, nullable=True)
    feature_full_simple = Column(String, nullable=True)
    limit_value = Column(Integer, nullable=False)
    tariff = relationship('Tariffs', back_populates='tariff_limits')

    __table_args__ = (
        Index('idx_tariff_limits_tariff_id', 'tariff_id'),
        UniqueConstraint("tariff_id", "feature_name", name="uq_tariff_limits_tariff_feature")
    )


class Variables(Base):
    __tablename__ = "variables"

    variables_kit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    variables_kit_name = Column(String, nullable=False)
    variables_kit_description = Column(String, nullable=True)
    variables_details = relationship('VariablesDetails', back_populates='variables', cascade='all, delete-orphan', lazy='select')
    project_id = Column(UUID(as_uuid=True), nullable=False)

    __table_args__ = (
        Index('ix_variables_project', 'project_id'),
    )


class VariablesDetails(Base):
    __tablename__ = "variables_details"
    variable_details_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    variables_kit_id = Column(UUID(as_uuid=True), ForeignKey("variables.variables_kit_id"), nullable=False)
    variable_name = Column(String, nullable=False)
    variable_value = Column(String, nullable=True)
    variable_config = Column(JSON, default=dict, nullable=False)
    variable_description = Column(String, nullable=True)
    variables = relationship('Variables', back_populates='variables_details')

    __table_args__ = (
        Index('idx_variables_details_tariff_id', 'variables_kit_id'),
        Index('idx_variables_details_tariff_id_feature_name', 'variables_kit_id', 'variable_name'),
    )


class Role(Base):
    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String, nullable=False, unique=True)
    permission = Column(JSON)
    description = Column(String)


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean(), default=True)
    # active_workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.workspace_id"), nullable=False)
    active_workspace_id = Column(UUID(as_uuid=True), nullable=False)
    extra = Column(JSON, default=dict, nullable=True)
    source = Column(String, nullable=True)
    host = Column(String, nullable=True)

    # projects = relationship("Project", back_populates="user")
    # happy_passes = relationship("HappyPass", back_populates="user")
    # billing_transactions = relationship("BillingTransactions", back_populates="user")
    # workspaces = relationship("Workspace", back_populates="users")
    # memberships = relationship("WorkspaceMembership", back_populates="user")
    # project_users = relationship("ProjectUser", back_populates="user")


class FlagCatalog(Base):
    __tablename__ = 'flag_catalog'

    flag_name = Column(String(50), primary_key=True)
    description = Column(String(255), nullable=True)
    default_shown = Column(Boolean, default=False)
    default_view_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserFlags(Base):
    __tablename__ = "user_flags"
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), primary_key=True, nullable=False)
    flags = Column(JSON, default=dict, nullable=False)


class Environment(Base):
    __tablename__ = "environments"

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    environment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    browser = Column(String, nullable=False)
    operation_system = Column(String, nullable=False)
    resolution = Column(JSON, default=dict, nullable=False)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    retry_enabled = Column(Boolean, nullable=False, default=False)
    retry_timeout = Column(Integer, nullable=True)

    __table_args__ = (
        Index('ix_project', 'project_id'),
    )


class Project(Base):
    __tablename__ = "projects"

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    project_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'))
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.workspace_id'))
    parallel_exec = Column(Integer, default=0)
    # user = relationship('User', back_populates='projects')
    suites = relationship('Suite', back_populates='project', cascade='all, delete-orphan', lazy="select")
    # workspace = relationship('Workspace', back_populates='projects')

    __table_args__ = (
        Index('ix_projects_user_id', 'user_id'),
        Index('ix_projects_name', 'name'),
        Index('ix_workspace_id', 'workspace_id'),
        Index('ix_project_id_workspace_id', 'project_id', 'workspace_id'),
        Index('idx_project_id_name_description', 'project_id', 'name', 'description'),

    )


class Suite(Base):
    __tablename__ = "suites"

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    suite_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.project_id'))
    parent_id = Column(UUID(as_uuid=True), ForeignKey('suites.suite_id'), nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    position = Column(Integer, nullable=False, default=0)

    project = relationship('Project', back_populates='suites')
    cases = relationship('Case', back_populates='suite', cascade='all, delete-orphan', lazy="select")

    children = relationship('Suite', back_populates='parent', cascade='all, delete-orphan', lazy='select')
    parent = relationship('Suite', remote_side=[suite_id], back_populates='children')

    __table_args__ = (
        Index('ix_suites_position_parent_id', 'position', 'parent_id'),
        Index('ix_suites_project', 'project_id'),
        Index('ix_suites_parent_id', 'parent_id'),
        Index('ix_suites_name', 'name')
    )


class Case(Base):
    __tablename__ = "cases"

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    case_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suite_id = Column(UUID(as_uuid=True), ForeignKey('suites.suite_id'))
    project_id = Column(UUID(as_uuid=True), nullable=True)
    name = Column(String, nullable=False)
    context = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    before_browser_start = Column(JSON, default=list, nullable=True)
    before_steps = Column(JSON, default=list, nullable=True)
    steps = Column(JSON, nullable=False)
    after_steps = Column(JSON, default=list, nullable=True)
    validation_steps = Column(JSON, default=list, nullable=True)
    validation_task = Column(String, nullable=True)
    type = Column(String, nullable=True, default="automated")
    status = Column(String, nullable=True, default="Draft")
    priority = Column(String, nullable=True, default="Low")
    url = Column(String, nullable=True)
    variables = Column(String, nullable=True, default="Default")
    llm_response = Column(JSON, nullable=True)
    is_valid = Column(Boolean, default=True, nullable=False)
    validation_reason = Column(JSON, default=dict, nullable=False)
    action_plan = Column(JSON, nullable=True)
    action_plan_id = Column(UUID(as_uuid=True), nullable=True)
    external_id = Column(String, nullable=True)
    position = Column(Integer, nullable=False, default=0)
    shared_steps = Column(JSON, default=list, nullable=True)
    environment_id = Column(UUID(as_uuid=True), nullable=True)

    suite = relationship('Suite', back_populates='cases')
    shared_steps_links = relationship(
        "CaseSharedSteps",
        back_populates="case",
        cascade="all, delete-orphan",
        lazy="select",
        passive_deletes=True,
    )

    __table_args__ = (
        Index('ix_cases_suite_id', 'suite_id'),
        Index('ix_cases_position_suite_id', 'position', 'suite_id'),
        Index('ix_cases_name', 'name'),
        Index('ix_cases_project_id', 'project_id'),
        Index('idx_cases_case_id_suite_id', 'case_id', 'suite_id'),

        UniqueConstraint('external_id', 'project_id', name='uc_case_external_id_project'),
    )


class SharedSteps(Base):
    __tablename__ = "shared_steps"

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    shared_steps_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    steps = Column(JSON, nullable=False)
    is_valid = Column(Boolean, default=True, nullable=False)
    validation_reason = Column(JSON, default=dict, nullable=False)
    action_plan = Column(JSON, nullable=True)
    action_plan_id = Column(UUID(as_uuid=True), nullable=True)

    case_links = relationship(
        "CaseSharedSteps",
        back_populates="shared_steps",
        lazy="select",
        cascade="save-update, merge",  # поймаем IntegrityError если есть в CaseSharedSteps
        passive_deletes=True,
    )

    __table_args__ = (

        Index('ix_shared_steps_project_id', 'project_id'),
        Index('ix_shared_steps_name_project_id', 'name', 'project_id'),
        Index('idx_shared_steps_shared_steps_id_project_id', 'shared_steps_id', 'project_id'),
    )


class CaseSharedSteps(Base):
    __tablename__ = "case_shared_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False)
    shared_steps_id = Column(UUID(as_uuid=True), ForeignKey("shared_steps.shared_steps_id", ondelete="RESTRICT"), nullable=False)

    case = relationship("Case", back_populates="shared_steps_links")
    shared_steps = relationship("SharedSteps", back_populates="case_links")

    __table_args__ = (
        Index('ix_case_shared_steps_case_id', 'case_id'),
        Index('ix_case_shared_steps_shared_steps_id', 'shared_steps_id'),
    )


class HappyPass(Base):
    __tablename__ = "happy_pass"

    happy_pass_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    name = Column(String, nullable=False)
    context = Column(Text)
    # Список JSON { "bucket": "some_bucket", "filename": "some_file.png" }
    images = Column(ARRAY(JSON), nullable=False)
    full_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    steps = Column(JSON, nullable=True)
    action_plan = Column(JSON, nullable=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.workspace_id'))
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.project_id'), nullable=False)
    language = Column(String, nullable=True)

    # user = relationship('User', back_populates='happy_passes')
    # subsuites = relationship('SubSuite', back_populates='happy_pass_relation')

    __table_args__ = (
        Index('ix_happy_pass_user_id', 'user_id'),
        Index('ix_happy_pass_created_at', 'created_at'),
        Index('ix_happy_pass_user_id_created_at', 'user_id', 'project_id', 'created_at'),

        Index('ix_happy_pass_workspace_created', 'workspace_id', desc('created_at')),
        Index('ix_happy_pass_workspace_project', 'workspace_id', 'project_id')
    )


class GroupRunCase(Base):
    __tablename__ = "group_run_cases"

    group_run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True)

    user_id = Column(UUID(as_uuid=True), nullable=False)
    author = Column(String, nullable=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default='untested')

    environment = Column(UUID(as_uuid=True), nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=True)
    use_parallel_flag = Column(Boolean, default=False, nullable=False)
    parallel_exec = Column(Integer, default=0, nullable=False)

    current_phase = Column(String, nullable=True)  # None | 'sequential' | 'parallel'
    parallel_started_at = Column(DateTime(timezone=True), nullable=True)

    host = Column(String, nullable=True)
    extra = Column(String, nullable=True)
    variables = Column(String, nullable=True)
    background_video_generate = Column(Boolean, default=True)

    cases = relationship("GroupRunCaseCase", back_populates="group_run_case", cascade="all, delete-orphan", lazy="select")

    __table_args__ = (
        Index('ix_group_run_cases_project_id', 'project_id'),
        Index('idx_group_run_cases_group_run_id', 'group_run_id'),
        Index('idx_group_run_created_at', 'created_at'),
        Index('idx_group_run_updated_at', 'updated_at'),
        Index('idx_group_run_status', 'status'),
        Index('idx_group_run_deadline', 'deadline'),
        Index('idx_group_run_author', 'author'),
        Index('idx_group_run_name', 'name'),
        Index('idx_group_run_name_description', 'name', 'description'),
        Index('idx_group_run_project_status', 'project_id', 'status'),
        Index('idx_group_run_project_created', 'project_id', 'created_at'),
        Index('idx_group_run_project_phase_created', 'project_id', 'current_phase', 'created_at'),
    )


class GroupRunCaseCase(Base):
    __tablename__ = "group_run_case_cases"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_run_id = Column(UUID(as_uuid=True), ForeignKey("group_run_cases.group_run_id"))
    case_id = Column(UUID(as_uuid=True), nullable=False)
    case_type_in_run = Column(String, nullable=False, default='automated')
    current_case_version = Column(JSON, nullable=False)
    suite_hierarchy = Column(JSON, nullable=False)

    execution_mode = Column(String, nullable=False, default='parallel')  # 'sequential' | 'parallel'
    execution_order = Column(Integer, nullable=True)  # only for sequential

    group_run_case = relationship("GroupRunCase", back_populates="cases")

    __table_args__ = (
        Index('idx_grcc_group_mode_order', 'group_run_id', 'execution_mode', 'execution_order'),
    )


class RunCase(Base):
    __tablename__ = "run_cases"

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_run_id = Column(UUID(as_uuid=True), nullable=True)
    case_id = Column(UUID(as_uuid=True), nullable=False)
    group_run_case_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String, nullable=True)
    run_summary = Column(String, nullable=True)
    video = Column(JSON, nullable=True)
    steps = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    start_dt = Column(DateTime(timezone=True))
    end_dt = Column(DateTime(timezone=True))
    complete_time = Column(FLOAT)
    current_case_version = Column(JSON, nullable=True)
    cnt_run = Column(Integer, default=0)
    attachments = Column(JSON, default=list, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), nullable=True)
    extra = Column(String, nullable=True)
    project_id = Column(UUID(as_uuid=True), nullable=True)
    background_video_generate = Column(Boolean, default=True)

    execution_mode = Column(String, nullable=True)   # 'sequential' | 'parallel'
    execution_order = Column(Integer, nullable=True)  # only for sequential
    case_type_in_run = Column(String, nullable=False, default='automated')

    # case = relationship('Case', back_populates='run_cases')

    __table_args__ = (
        Index('ix_run_cases_user_id', 'user_id'),
        Index('ix_run_cases_cnt_run', 'cnt_run'),
        Index('ix_run_cases_start_dt', 'start_dt'),
        Index('ix_run_cases_created_at', 'created_at'),
        Index('ix_run_cases_case_id', 'case_id'),
        Index('ix_run_cases_group_run_case_id', 'group_run_case_id'),
        Index('ix_run_cases_end_dt', 'end_dt'),
        Index('ix_run_cases_status', 'status'),
        Index('idx_run_cases_status_type_created', 'status', 'case_type_in_run', 'created_at'),
        Index('idx_run_cases_group_run_id_status_workspace_id', 'group_run_id', 'status', 'workspace_id'),
        Index('idx_run_cases_start_dt_run_id', 'start_dt', 'run_id'),
        Index('idx_run_cases_start_dt_case_id', 'start_dt', 'case_id'),
        Index('idx_run_cases_start_dt_group_run_case_id', 'start_dt', 'group_run_case_id'),
        Index('idx_run_cases_created_at_run_id', 'created_at', 'run_id'),
        Index('idx_run_cases_created_at_case_id', 'created_at', 'case_id'),
        Index('idx_run_cases_created_at_group_run_case_id', 'created_at', 'group_run_case_id'),
        Index('idx_run_cases_group_case_created_at', 'group_run_id', 'case_id', 'created_at'),
        Index('idx_run_cases_group_case_created_at_group_run_case_id', 'group_run_id', 'group_run_case_id', 'created_at'),
        Index('idx_run_cases_status_created_at', 'status', 'created_at'),
        # Index('ix_run_cases_case_type', text("(current_case_version->>'case_type_in_run')"))
        Index('idx_run_cases_group_mode_status_ws', 'group_run_id', 'execution_mode', 'status', 'workspace_id'),
        Index('idx_run_cases_group_mode_order_created', 'group_run_id', 'execution_mode', 'execution_order', 'created_at')
    )


class UserDemo(Base):
    __tablename__ = "users_demo"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True)
    username = Column(String, nullable=False)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())


class ModelResultDemo(Base):
    __tablename__ = "model_results_demo"

    result_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users_demo.user_id"), nullable=False)
    email = Column(String, nullable=False)
    result_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    like = Column(Integer, default=0)


class UserToken(Base):
    __tablename__ = 'user_tokens'

    token_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id', ondelete='CASCADE'), index=True)
    name = Column(String, nullable=False)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_user_tokens_user_id_created_at", "user_id", "created_at"),
    )


class Templates(Base):
    __tablename__ = "templates"

    template_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_type = Column(String, nullable=False)
    template_data = Column(JSON, nullable=False)


class BillingTransactions(Base):
    __tablename__ = "billing_transactions"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.user_id'), nullable=False)
    source = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    details = Column(JSON, nullable=True)

    # user = relationship('User', back_populates='billing_transactions')

    __table_args__ = (
        Index('ix_billing_transactions_user_id', 'user_id'),
        Index('ix_billing_transactions_created_at', 'created_at'),
        Index('ix_billing_transactions_user_id_created_at', 'user_id', 'created_at'),
        Index('ix_billing_transactions_user_id_created_at_amount', 'user_id', 'created_at', 'amount'),
        Index('ix_billing_transactions_user_id_amount', 'user_id', 'amount'),
    )


class PaymentHistory(Base):
    __tablename__ = "payment_history"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number = Column(String(15), unique=True, nullable=False,
                            server_default=Sequence('invoice_seq', start=1, increment=1, minvalue=1, maxvalue=10**15 - 1, cycle=False, cache=1).next_value())
    x_requests_id = Column(UUID(as_uuid=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    workspace_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)

    corporate_invoice_flag = Column(Boolean(), default=False)

    services = Column(String, nullable=False)
    tariff_id = Column(UUID(as_uuid=True), nullable=False)
    stream_count = Column(Integer, nullable=True)
    cnt_months = Column(Integer, nullable=False)
    stream_only = Column(Boolean(), default=False)

    cur = Column(String, nullable=True)
    discount_amount = Column(Numeric(scale=2), nullable=True)
    discount_percent = Column(Integer, nullable=True)
    amount = Column(Numeric(scale=2), nullable=False)

    status = Column(String, nullable=False)
    invoice_id = Column(UUID(as_uuid=True), nullable=True)
    payment_dt = Column(DateTime(timezone=True))
    due_date = Column(DateTime(timezone=True))
    invoice_date = Column(DateTime(timezone=True))
    pdf = Column(JSON, default=dict, nullable=True)

    # физики
    payment_id = Column(String(20), nullable=True)
    payment_url = Column(String(100), nullable=True)

    details = Column(JSON, nullable=True)
    response = Column(JSON, nullable=True)
    status_code = Column(Integer, nullable=True)

    last_check_at = Column(DateTime(timezone=True))
    email = Column(String, nullable=True)

    __table_args__ = (
        Index('ix_payment_history_workspace_id', 'workspace_id'),
        Index('ix_payment_history_created_at', 'created_at'),
        Index('ix_payment_history_status', 'status'),
        Index('ix_payment_history_workspace_id_status', 'workspace_id', 'status'),
        Index('ix_payment_history_workspace_status_due_date', 'status', 'due_date'),
        Index('ix_payment_history_workspace_status_last_check_at', 'status', 'last_check_at'),
    )
