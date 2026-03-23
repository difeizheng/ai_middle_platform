"""
智能体工厂 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
import time

from app.core.database import get_db
from app.models.agent import Agent, AgentFlow, AgentExecution, AgentMemory, AgentTool
from app.models.user import User
from app.auth.dependencies import get_current_user
from app.api.middleware import rate_limit
from app.services.agents.engine import AgentEngine
from app.services.agents.flow_engine import FlowEngine
from app.services.agents.tools import ToolRegistry

router = APIRouter()


# ========== 智能体管理 ==========

@router.get("/agents")
@rate_limit(max_requests=60, window=60)
async def list_agents(
    skip: int = 0,
    limit: int = 20,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取智能体列表"""
    query = select(Agent).where(Agent.is_active == is_active)

    if limit > 100:
        limit = 100

    result = await db.execute(query.offset(skip).limit(limit))
    agents = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "role": a.role,
                "model_id": a.model_id,
                "tools": a.tools,
                "created_at": str(a.created_at),
            }
            for a in agents
        ],
        "total": len(agents),
    }


@router.post("/agents")
async def create_agent(
    name: str = Body(..., description="智能体名称"),
    description: str = Body(None, description="智能体描述"),
    role: str = Body("executor", description="角色：planner, executor, reviewer, summarizer"),
    model_id: int = Body(None, description="绑定的模型 ID"),
    config: Dict[str, Any] = Body(default_factory=dict, description="智能体配置"),
    tools: List[Dict] = Body(default_factory=list, description="绑定工具列表"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建智能体"""
    agent = Agent(
        name=name,
        description=description,
        role=role,
        model_id=model_id,
        config=config,
        tools=tools,
        created_by=current_user.id,
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return {
        "success": True,
        "data": {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "role": agent.role,
            "config": agent.config,
            "tools": agent.tools,
            "created_at": str(agent.created_at),
        },
    }


@router.get("/agents/{agent_id}")
async def get_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取智能体详情"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="智能体不存在")

    return {
        "success": True,
        "data": {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "role": agent.role,
            "model_id": agent.model_id,
            "config": agent.config,
            "tools": agent.tools,
            "created_at": str(agent.created_at),
            "updated_at": str(agent.updated_at) if agent.updated_at else None,
        },
    }


@router.put("/agents/{agent_id}")
async def update_agent(
    agent_id: int,
    name: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    role: Optional[str] = Body(None),
    config: Optional[Dict[str, Any]] = Body(None),
    tools: Optional[List[Dict]] = Body(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新智能体"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="智能体不存在")

    # 更新字段
    if name is not None:
        agent.name = name
    if description is not None:
        agent.description = description
    if role is not None:
        agent.role = role
    if config is not None:
        agent.config = config
    if tools is not None:
        agent.tools = tools

    agent.updated_at = func.now()

    await db.commit()
    await db.refresh(agent)

    return {
        "success": True,
        "data": {
            "id": agent.id,
            "name": agent.name,
            "updated_at": str(agent.updated_at),
        },
    }


@router.delete("/agents/{agent_id}")
async def delete_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除智能体（软删除）"""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="智能体不存在")

    agent.is_active = False
    await db.commit()

    return {
        "success": True,
        "message": "智能体已删除",
    }


# ========== 智能体执行 ==========

@router.post("/agents/{agent_id}/execute")
@rate_limit(max_requests=30, window=60)
async def execute_agent(
    agent_id: int,
    task: str = Body(..., description="任务描述"),
    session_id: Optional[str] = Body(None, description="会话 ID"),
    stream: bool = Body(False, description="是否流式输出"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """执行智能体任务"""
    # 获取智能体配置
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="智能体不存在")

    if not agent.is_active:
        raise HTTPException(status_code=400, detail="智能体未激活")

    try:
        # 创建智能体引擎
        engine = AgentEngine(
            agent_id=agent.id,
            name=agent.name,
            role=agent.role,
            config=agent.config or {},
            tools=agent.tools or [],
        )

        # 执行任务
        from ...services.agents.engine import AgentContext
        context = AgentContext(
            session_id=session_id or str(time.time()),
            task=task,
        )

        response = await engine.execute(task, context, stream)

        # 记录执行历史
        execution = AgentExecution(
            agent_id=agent_id,
            status=response.status.value,
            input_data={"task": task},
            output_data={"content": response.content},
            started_at=time.time(),
            completed_at=time.time(),
        )
        db.add(execution)
        await db.commit()

        return {
            "success": True,
            "data": {
                "content": response.content,
                "status": response.status.value,
                "metadata": response.metadata,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行失败：{str(e)}",
        )


# ========== 流程管理 ==========

@router.get("/flows")
async def list_flows(
    skip: int = 0,
    limit: int = 20,
    is_active: bool = True,
    is_template: bool = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取流程列表"""
    query = select(AgentFlow).where(AgentFlow.is_active == is_active)

    if is_template is not None:
        query = query.where(AgentFlow.is_template == is_template)

    if limit > 100:
        limit = 100

    result = await db.execute(query.offset(skip).limit(limit))
    flows = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": f.id,
                "name": f.name,
                "description": f.description,
                "version": f.version,
                "is_template": f.is_template,
                "created_at": str(f.created_at),
            }
            for f in flows
        ],
        "total": len(flows),
    }


@router.post("/flows")
async def create_flow(
    name: str = Body(..., description="流程名称"),
    description: str = Body(None, description="流程描述"),
    nodes: List[Dict] = Body(default_factory=list, description="节点定义"),
    edges: List[Dict] = Body(default_factory=list, description="连接关系"),
    variables: List[Dict] = Body(default_factory=list, description="流程变量"),
    is_template: bool = Body(False, description="是否为模板"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建流程"""
    flow = AgentFlow(
        name=name,
        description=description,
        nodes=nodes,
        edges=edges,
        variables=variables,
        is_template=is_template,
        created_by=current_user.id,
    )

    db.add(flow)
    await db.commit()
    await db.refresh(flow)

    return {
        "success": True,
        "data": {
            "id": flow.id,
            "name": flow.name,
            "nodes": flow.nodes,
            "edges": flow.edges,
            "created_at": str(flow.created_at),
        },
    }


@router.get("/flows/{flow_id}")
async def get_flow(
    flow_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取流程详情"""
    result = await db.execute(select(AgentFlow).where(AgentFlow.id == flow_id))
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="流程不存在")

    return {
        "success": True,
        "data": {
            "id": flow.id,
            "name": flow.name,
            "description": flow.description,
            "version": flow.version,
            "nodes": flow.nodes,
            "edges": flow.edges,
            "variables": flow.variables,
            "is_template": flow.is_template,
            "created_at": str(flow.created_at),
            "updated_at": str(flow.updated_at) if flow.updated_at else None,
        },
    }


@router.post("/flows/{flow_id}/execute")
async def execute_flow(
    flow_id: int,
    inputs: Dict[str, Any] = Body(default_factory=dict, description="输入数据"),
    variables: Dict[str, Any] = Body(default_factory=dict, description="流程变量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """执行流程"""
    # 获取流程定义
    result = await db.execute(select(AgentFlow).where(AgentFlow.id == flow_id))
    flow = result.scalar_one_or_none()

    if not flow:
        raise HTTPException(status_code=404, detail="流程不存在")

    if not flow.is_active:
        raise HTTPException(status_code=400, detail="流程未激活")

    try:
        # 创建流程引擎
        engine = FlowEngine(
            flow_id=flow.id,
            name=flow.name,
            nodes=flow.nodes or [],
            edges=flow.edges or [],
            variables=flow.variables or [],
        )

        # 执行流程
        result = await engine.execute(inputs, variables)

        # 记录执行历史
        execution = AgentExecution(
            flow_id=flow_id,
            status=result.status.value,
            input_data=inputs,
            output_data=result.outputs,
            logs=result.logs,
            started_at=time.time(),
            completed_at=time.time(),
            duration_ms=result.duration_ms,
            error_message=result.error_message,
        )
        db.add(execution)
        await db.commit()

        return {
            "success": True,
            "data": {
                "execution_id": result.execution_id,
                "status": result.status.value,
                "outputs": result.outputs,
                "duration_ms": result.duration_ms,
                "error_message": result.error_message,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行失败：{str(e)}",
        )


# ========== 工具管理 ==========

@router.get("/tools")
async def list_tools_endpoint(
    current_user: User = Depends(get_current_user),
):
    """获取可用工具列表"""
    tools = list_tools()

    return {
        "success": True,
        "data": tools,
    }


@router.post("/tools/execute")
async def execute_tool(
    tool_name: str = Body(..., description="工具名称"),
    params: Dict[str, Any] = Body(default_factory=dict, description="工具参数"),
    current_user: User = Depends(get_current_user),
):
    """执行工具"""
    try:
        registry = ToolRegistry()
        result = await registry.execute(tool_name, params)

        return {
            "success": True,
            "data": result,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"执行失败：{str(e)}",
        )


# ========== 执行历史 ==========

@router.get("/executions")
async def list_executions(
    flow_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取执行历史"""
    query = select(AgentExecution)

    if flow_id is not None:
        query = query.where(AgentExecution.flow_id == flow_id)
    if agent_id is not None:
        query = query.where(AgentExecution.agent_id == agent_id)

    query = query.order_by(AgentExecution.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    executions = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": e.id,
                "flow_id": e.flow_id,
                "agent_id": e.agent_id,
                "status": e.status,
                "duration_ms": e.duration_ms,
                "started_at": str(e.started_at) if e.started_at else None,
                "completed_at": str(e.completed_at) if e.completed_at else None,
            }
            for e in executions
        ],
        "total": len(executions),
    }
