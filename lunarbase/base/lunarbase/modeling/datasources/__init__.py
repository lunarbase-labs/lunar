from abc import abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Union
from uuid import uuid4

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator, field_serializer,
)
from pydantic_core.core_schema import ValidationInfo

from lunarcore.component.data_types import File
from lunarbase.modeling.datasources.attributes import (
    LocalFileConnectionAttributes,
    PostgresqlConnectionAttributes,
)
from lunarbase.utils import to_camel


class DataSourceType(Enum):
    # Keep the values consistent with the DataSource class types
    LOCAL_FILE = "LocalFile"
    POSTGRESQL = "Postgresql"

    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

    def expected_connection_attributes(self):
        if self == DataSourceType.LOCAL_FILE:
            return LocalFileConnectionAttributes, [
                field_name
                for field_name, filed_info in LocalFileConnectionAttributes.model_fields.items()
                if filed_info.is_required()
            ]
        elif self == DataSourceType.POSTGRESQL:
            return PostgresqlConnectionAttributes, [
                field_name
                for field_name, filed_info in PostgresqlConnectionAttributes.model_fields.items()
                if filed_info.is_required()
            ]
        else:
            return None, []



class DataSource(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(default=...)
    description: str = Field(default=...)
    type: Union[DataSourceType, str] = Field(default=...)
    connection_attributes: Union[BaseModel, Dict[str, Any]] = Field(
        default_factory=dict
    )

    class Config:
        alias_generator = to_camel
        populate_by_name = True
        validate_assignment = True
        arbitrary_attributes_allowed = True
        extra = "forbid"

    @classmethod
    def polymorphic_validation(cls, obj_dict: Dict):
        try:
            base_class = obj_dict["type"]
            if isinstance(base_class, str):
                base_class = DataSourceType[base_class.upper()]
            base_class = base_class.value
        except (KeyError, AttributeError):
            raise ValueError(
                f"Invalid DataSource {obj_dict}! Expected one of {DataSourceType.list()}"
            )

        subcls = {sub.__name__: sub for sub in cls.__subclasses__()}
        if base_class not in subcls:
            raise ValueError(
                f"Invalid DataSource type {base_class}! Expected one of {DataSourceType.list()}"
            )
        for subclass_name, subcls in subcls.items():
            if subclass_name == base_class:
                return subcls.model_validate(obj_dict)

    @field_serializer("type")
    @classmethod
    def serialize_type(cls, value):
        if isinstance(value, Enum):
            return value.name
        return value

    @field_validator("type")
    @classmethod
    def validate_type(cls, value):
        if isinstance(value, str):
            try:
                value = DataSourceType[value.upper()]
            except KeyError:
                raise ValueError(
                    f"Invalid DataSource type {value}! Expected one of {DataSourceType.list()}"
                )

        subcls = {sub.__name__ for sub in cls.__subclasses__()}
        if len(subcls) == 0:
            subcls = DataSourceType.list()
        if value.value not in subcls:
            raise ValueError(
                f"Invalid DataSource type {value}! Expected one of {DataSourceType.list()}"
            )
        return value

    @field_validator("connection_attributes")
    @classmethod
    def validate_connection_attributes(cls, value, info: ValidationInfo):
        if not isinstance(value, dict):
            try:
                value = value.model_dump()
            except AttributeError:
                raise ValueError(
                    f"Connection_attributes must be a dictionary! Got {type(value)} instead!"
                )

        _type = info.data.get("type")
        if _type is None:
            raise ValueError(
                f"Invalid type {_type} for DataSource {info.data.get('name', '<>')}. Expected one of {DataSourceType.list()}"
            )

        expected_connection_type, _expected = _type.expected_connection_attributes()
        _name = info.data.get("name", "")
        try:
            return expected_connection_type.model_validate(value)
        except ValueError as e:
            raise ValueError(
                f"Invalid connection attributes for DataSource {_name}: {e}!"
            )


    @abstractmethod
    def to_component_input(self, **kwargs: Any):
        pass


class LocalFile(DataSource):
    name: str = Field(default="Local file datasource")
    type: Union[str, DataSourceType] = Field(
        default_factory=lambda: DataSourceType.LOCAL_FILE,
        frozen=True,
    )
    description: str = Field(
        default="Local file datasource - allows read and write operations on local files."
    )
    connection_attributes: Union[Dict, LocalFileConnectionAttributes] = Field(
        default=...
    )

    def to_component_input(self, base_path: str):
        if not Path(base_path).exists():
            raise FileNotFoundError(f"Base path for file {self.name} does not exist!")

        _path = Path(base_path, self.connection_attributes.file_name)
        if not _path.exists():
            raise FileNotFoundError(f"File {self.name} does not exist on the server!")

        _size = Path(_path).stat().st_size
        return File(
            name=self.connection_attributes.file_name,
            description=self.description,
            type=self.connection_attributes.file_type,
            size=_size,
            path=str(_path),
        )


class Postgresql(DataSource):
    name: str = Field(default="Postgresql datasource")
    type: DataSourceType = Field(
        default_factory=lambda: DataSourceType.POSTGRESQL,
        frozen=True,
    )
    description: str = Field(
        default="Postgresql or SQLite datasource - allows read and write operations on a Postgresql or a local SQLite database."
    )
    connection_attributes: Union[Dict, PostgresqlConnectionAttributes] = Field(
        default=...
    )

    def to_component_input(self, **kwargs: Any):
        pass
