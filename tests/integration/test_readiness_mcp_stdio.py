"""Actual owned stdio + readonly inventory; fault scripts are trusted test doubles."""

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from apps.jarvis_mcp import readiness_client as client_module
from apps.jarvis_mcp import readiness_contracts as c
from apps.jarvis_mcp.readiness_client import FixedReadinessMcpClient

BINDING = c.ReadinessBinding("operator://owned-readiness", "session://owned-readiness")

# Finite owned fault program, never a production command-selection parameter.
FAULT_PROGRAM = r'''
import importlib.util,json,sys,time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8",newline="\n")
base=Path(sys.argv[1]); mode=sys.argv[2]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 module=importlib.util.module_from_spec(spec);sys.modules[name]=module
 spec.loader.exec_module(module);return module
c=load("readiness_contracts",base/"readiness_contracts.py")
s=load("owned_readiness_server",base/"readiness_server.py")
server=s.ReadinessServer()
sys.stderr.write("token=owned-private-stderr\n");sys.stderr.flush()
for raw in sys.stdin.buffer:
 message=json.loads(raw);method=message["method"]
 response=server.handle(message)
 if response is None:continue
 if method=="initialize":
  if mode=="wrong_id":response["id"]=99
  if mode=="bool_id":response["id"]=True
  if mode=="wrong_version":response["result"]["protocolVersion"]="foreign"
  if mode=="wrong_server":response["result"]["serverInfo"]["name"]="foreign"
  if mode=="capabilities":response["result"]["capabilities"]["sampling"]={}
  if mode=="server_request":response={"jsonrpc":"2.0","id":99,"method":"roots/list"}
  if mode=="invalid_utf8":sys.stdout.buffer.write(b"\xff\n");sys.stdout.flush();continue
  if mode=="oversized":sys.stdout.write("x"*65537+"\n");sys.stdout.flush();continue
  if mode=="malformed":sys.stdout.write("not JSON\n");sys.stdout.flush();continue
  if mode=="duplicate":
   sys.stdout.write('{"jsonrpc":"2.0","id":1,"id":1,"result":{}}\n')
   sys.stdout.flush();continue
 if method=="tools/list":
  if mode=="descriptor":response["result"]["tools"][0]["inputSchema"]["additionalProperties"]=True
  if mode=="extra_tool":response["result"]["tools"].append({"name":"execute"})
  if mode=="pagination":response["result"]["nextCursor"]="foreign"
  if mode=="annotation":response["result"]["tools"][0]["annotations"]["readOnlyHint"]=1
 if method=="tools/call":
  if mode=="timeout":time.sleep(30)
  result=response["result"]
  if mode in ("origin","authority","runtime","selected","count"):
   doc=result["structuredContent"]
   key,value={"origin":("origin","https"),"authority":("authority","all"),
     "runtime":("runtime_verified",True),"selected":("front_id","F01"),
     "count":("counts",{})}[mode]
   doc[key]=value;result["content"][0]["text"]=json.dumps(doc)
  if mode=="mirror":result["content"][0]["text"]='{"private":"untrusted-rejected-text"}'
  if mode=="raw_duplicate":
   text=result["content"][0]["text"]
   result["content"][0]["text"]=text[:-1]+',"authority":"none"}'
  if mode=="media":result["content"]=[{"type":"image","data":"untrusted-rejected-text"}]
  if mode=="iserror":
   result={"isError":True,"content":[{"type":"text","text":"untrusted-rejected-text"}]}
   response["result"]=result
 sys.stdout.write(json.dumps(response,ensure_ascii=False,separators=(",",":"))+"\n")
 sys.stdout.flush()
'''


def inject_fault(monkeypatch, scenario):
    original, spawned = asyncio.create_subprocess_exec, []
    async def create(*args, **kwargs):
        # Assert the app requested exactly its fixed script before substituting
        # an owned adversarial test double with the same stdio/env constraints.
        assert args[1:3] == ("-I", "-B")
        script = Path(args[3])
        assert script.name == "readiness_server.py" and script.is_absolute()
        assert args[4:] == ("--authorized",)
        process = await original(args[0], "-I", "-B", "-c", FAULT_PROGRAM,
                                 str(script.parent), scenario, **kwargs)
        spawned.append((process, kwargs["cwd"]))
        return process
    monkeypatch.setattr(client_module.asyncio, "create_subprocess_exec", create)
    return spawned


@pytest.mark.parametrize("selection", ["all", "F01", "F13", "T03"])
def test_real_fixed_server_inventory_read_binding_and_cleanup(selection):
    async def prove():
        value = FixedReadinessMcpClient(BINDING, authorized=True, timeout_seconds=10)
        try:
            await value.start()
            directory = value._directory.name
            assert value.process_running and value.binding == BINDING
            observation = await value.call(BINDING, c.TOOL_NAME, {"front_id": selection})
            assert observation.request_id == 3 and observation.binding == BINDING
            assert observation.snapshot() == c.build_snapshot(selection)
            assert observation.metadata()["authority"] == "none"
            assert observation.evidence_mode == "local_repository_snapshot"
        finally:
            await value.close()
        assert not value.process_running and not Path(directory).exists()
        assert [event.stage for event in value.events] == ["initialize", "call", "close"]
        assert "operator://" not in repr(value.events)
    asyncio.run(prove())


def test_absolute_interpreter_fixed_script_minimal_env_temp_cwd(monkeypatch):
    original, calls = asyncio.create_subprocess_exec, []
    async def audit(*args, **kwargs):
        calls.append((args, kwargs))
        assert Path(args[0]).is_absolute() and Path(args[3]).is_absolute()
        assert args[1:3] == ("-I", "-B") and args[4:] == ("--authorized",)
        assert kwargs["shell"] is False and set(kwargs["env"]) <= {"SYSTEMROOT"}
        assert kwargs["stderr"] == asyncio.subprocess.DEVNULL
        assert Path(kwargs["cwd"]).is_dir()
        assert Path(kwargs["cwd"]) != c.readiness_module().ROOT
        return await original(*args, **kwargs)
    monkeypatch.setattr(client_module.asyncio, "create_subprocess_exec", audit)
    async def prove():
        async with FixedReadinessMcpClient(BINDING, authorized=True, timeout_seconds=10) as value:
            await value.call(BINDING, c.TOOL_NAME, {"front_id": "all"})
    asyncio.run(prove())
    assert len(calls) == 1


@pytest.mark.parametrize("scenario", [
    "wrong_id", "bool_id", "wrong_version", "wrong_server", "capabilities", "server_request",
    "invalid_utf8", "oversized", "malformed", "duplicate", "descriptor", "extra_tool",
    "pagination", "annotation",
])
def test_actual_stdio_bad_handshake_descriptor_never_returns_snapshot(monkeypatch, scenario):
    processes = inject_fault(monkeypatch, scenario)
    async def prove():
        value = FixedReadinessMcpClient(BINDING, authorized=True, timeout_seconds=10)
        with pytest.raises(c.ReadinessRejected):
            await value.start()
        assert not value.process_running
        assert value.events[-1].stage == "close"
        assert "private" not in repr(value.events) and "untrusted" not in repr(value.events)
    asyncio.run(prove())
    assert len(processes) == 1 and processes[0][0].returncode is not None
    assert not Path(processes[0][1]).exists()


@pytest.mark.parametrize("scenario", ["origin", "authority", "runtime", "selected", "count",
                                    "mirror", "raw_duplicate", "media", "iserror"])
def test_actual_stdio_bad_tool_snapshot_no_authority_or_content_leak(monkeypatch, scenario):
    processes = inject_fault(monkeypatch, scenario)
    async def prove():
        value = FixedReadinessMcpClient(BINDING, authorized=True, timeout_seconds=10)
        await value.start()
        with pytest.raises(c.ReadinessRejected) as error:
            await value.call(BINDING, c.TOOL_NAME, {"front_id": "all"})
        assert "private" not in str(error.value) and "untrusted" not in str(error.value)
        assert not value.process_running and value.events[-1].stage == "close"
        with pytest.raises(c.ReadinessRejected, match="^session_not_ready$"):
            await value.call(BINDING, c.TOOL_NAME, {"front_id": "all"})
    asyncio.run(prove())
    assert processes[0][0].returncode is not None and not Path(processes[0][1]).exists()


@pytest.mark.parametrize("invalid", ["binding", "scope", "tool", "args", "forged_binding"])
def test_negatives_before_tool_dispatch_session_stays_bounded(invalid):
    async def prove():
        async with FixedReadinessMcpClient(BINDING, authorized=True, timeout_seconds=10) as value:
            binding, tool, arguments = BINDING, c.TOOL_NAME, {"front_id": "all"}
            if invalid == "binding":
                binding = replace(BINDING, session_ref="session://foreign")
            elif invalid == "scope":
                binding = object()
            elif invalid == "tool":
                tool = "execute"
            elif invalid == "args":
                arguments["path"] = "private"
            else:
                object.__setattr__(value.binding, "principal_ref", "operator://changed")
            with pytest.raises(c.ReadinessRejected):
                await value.call(binding, tool, arguments)
            assert value._next_id == 2
    asyncio.run(prove())


@pytest.mark.parametrize("action", ["timeout", "event", "task", "pre_cancel"])
def test_actual_timeout_and_cancellation_reap_only_owned_process(monkeypatch, action):
    processes = inject_fault(monkeypatch, "timeout")
    async def prove():
        value = FixedReadinessMcpClient(BINDING, authorized=True, timeout_seconds=10)
        await value.start()
        if action == "timeout":
            # Exercise the existing absolute deadline; no production budget is enlarged.
            value._deadline = asyncio.get_running_loop().time() + .2
        cancellation = asyncio.Event()
        if action == "pre_cancel":
            cancellation.set()
        task = asyncio.create_task(value.call(BINDING, c.TOOL_NAME, {"front_id": "all"},
                                               cancel=cancellation))
        if action in {"event", "task"}:
            await asyncio.sleep(.05)
            if action == "event":
                cancellation.set()
            else:
                task.cancel()
        with pytest.raises((c.ReadinessRejected, asyncio.CancelledError)):
            await task
        assert not value.process_running and value.events[-1].stage == "close"
    asyncio.run(prove())
    assert processes[0][0].returncode is not None and not Path(processes[0][1]).exists()


def test_pre_cancelled_start_never_spawns(monkeypatch):
    async def forbidden(*_args, **_kwargs):
        pytest.fail("pre-cancel started process")
    monkeypatch.setattr(client_module.asyncio, "create_subprocess_exec", forbidden)
    async def prove():
        value = FixedReadinessMcpClient(BINDING, authorized=True)
        flag = asyncio.Event()
        flag.set()
        with pytest.raises(c.ReadinessRejected, match="^cancelled$"):
            await value.start(cancel=flag)
        assert not value.process_running and value._directory is None
    asyncio.run(prove())


def test_actual_single_flight_no_queue_or_retry(monkeypatch):
    processes = inject_fault(monkeypatch, "timeout")
    async def prove():
        value = FixedReadinessMcpClient(BINDING, authorized=True, timeout_seconds=10)
        await value.start()
        flag = asyncio.Event()
        task = asyncio.create_task(value.call(BINDING, c.TOOL_NAME, {"front_id": "all"},
                                               cancel=flag))
        await asyncio.sleep(.05)
        with pytest.raises(c.ReadinessRejected, match="^concurrent_request_not_supported$"):
            await value.call(BINDING, c.TOOL_NAME, {"front_id": "F13"})
        assert value._next_id == 3
        flag.set()
        with pytest.raises(c.ReadinessRejected, match="^cancelled$"):
            await task
        await value.close()
        assert not value.process_running
    asyncio.run(prove())
    assert len(processes) == 1


def test_session_request_and_event_limits_are_not_evicted():
    async def prove():
        async with FixedReadinessMcpClient(BINDING, authorized=True, timeout_seconds=10) as value:
            value._next_id = c.MAX_REQUESTS
            with pytest.raises(c.ReadinessRejected, match="^request_limit_exceeded$"):
                await value.call(BINDING, c.TOOL_NAME, {"front_id": "all"})
            assert not value.process_running
        other = FixedReadinessMcpClient(BINDING, authorized=True, timeout_seconds=10)
        await other.start()
        other._events = [c.ReadinessEvent("initialize", "completed")] * (c.MAX_EVENTS - 2)
        with pytest.raises(c.ReadinessRejected, match="^event_limit_exceeded$"):
            await other.call(BINDING, c.TOOL_NAME, {"front_id": "all"})
        assert len(other.events) <= c.MAX_EVENTS and not other.process_running
    asyncio.run(prove())


def test_global_expired_budget_does_not_send_tool_call():
    async def prove():
        value = FixedReadinessMcpClient(BINDING, authorized=True, timeout_seconds=10)
        await value.start()
        sent = value._sent
        value._deadline = 0
        with pytest.raises(c.ReadinessRejected, match="^collection_timeout$"):
            await value.call(BINDING, c.TOOL_NAME, {"front_id": "all"})
        assert value._sent == sent and not value.process_running
    asyncio.run(prove())


def test_session_byte_cap_combines_sent_and_received_without_tool_dispatch():
    async def prove():
        value = FixedReadinessMcpClient(BINDING, authorized=True, timeout_seconds=10)
        await value.start()
        value._received = c.MAX_SESSION_BYTES - value._sent
        with pytest.raises(c.ReadinessRejected, match="^request_limit_exceeded$"):
            await value.call(BINDING, c.TOOL_NAME, {"front_id": "all"})
        assert not value.process_running and value._next_id == 3
        assert value.events[-2].status == "rejected"
    asyncio.run(prove())
