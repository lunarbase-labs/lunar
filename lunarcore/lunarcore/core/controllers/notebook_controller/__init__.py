from typing import Union, Dict
from lunarcore.config import LunarConfig, LUNAR_PACKAGE_NAME
from lunarcore.utils import get_config
from lunarcore.core.persistence import PersistenceLayer
from lunarcore.core.data_models import WorkflowModel
from lunarcore.utils import setup_logger
import nbformat
from fastapi import UploadFile
from io import BytesIO
from .workflow_notebook_generator import WorkflowNotebookGenerator, NotebookSetupModel
import asyncio
from pydantic import BaseModel, Field

logger = setup_logger("notebook-controller")

class JupyterServerConfigModel(BaseModel):
    host: str = Field("localhost", description="The host of the Jupyter server")
    port: int = Field(8888, description="The port of the Jupyter server")

class NotebookController:
    def __init__(self, config: Union[str, Dict, LunarConfig]):
        self._config = config
        if isinstance(self._config, str):
            self._config = get_config(settings_file_path=config)
        elif isinstance(self._config, dict):
            self._config = LunarConfig.parse_obj(config)

        self._persistence_layer = PersistenceLayer(config=self._config)
        self._notebook_generator = WorkflowNotebookGenerator()

    async def save(self, workflow: WorkflowModel, user_id: str):
        workflow = WorkflowModel.model_validate(workflow)

        user_env_path = self._persistence_layer.get_user_environment_path(user_id)
        workflow_venv_path = self._persistence_layer.get_workflow_venv(user_id, workflow.id)
        nb_setup = NotebookSetupModel(user_env_path=user_env_path, workflow_venv_path=workflow_venv_path)
        
        nb = self._notebook_generator.generate(
            workflow, nb_setup
        )
        
        file = UploadFile(
            filename="index.ipynb",
            file=BytesIO(nbformat.writes(nb).encode("utf-8"))
        )

        workflow_notebook_path = self._persistence_layer.get_user_workflow_notebook_path(
            workflow_id=workflow.id, user_id=user_id
        )
        
        await self._persistence_layer.save_file_to_storage(
            workflow_notebook_path, file
        )
        
        return {
            "workflow": workflow,
            "dag": workflow.get_dag(),
            "ordered": workflow.components_ordered(),
        }
    
    async def open(self, workflow: WorkflowModel, user_id: str, jupyterConfig: JupyterServerConfigModel):
        jupyterConfig = JupyterServerConfigModel(**jupyterConfig)
        nb_path = self._persistence_layer.get_user_workflow_notebook_path(
            workflow_id=workflow.id, user_id=user_id
        )
        nb_exists = await self._persistence_layer.file_exists(f"{nb_path}index.ipynb")
        if not nb_exists:
            await self.save(workflow, user_id)
        
        command = [
            "poetry", "run", "jupyter", "lab",
            f"--notebook-dir={nb_path}", 
            f"--ip={jupyterConfig.host}", 
            f"--port={jupyterConfig.port}"
        ]
        
        process = await asyncio.create_subprocess_exec(*command)
        await process.wait()


