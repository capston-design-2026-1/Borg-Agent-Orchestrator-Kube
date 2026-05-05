import asyncio
import json

from orchestrator.layer2.aiopslab_contract import AIOpsLabPolicyAgent, initialize_aiopslab_problem


class FakeOrchestrator:
    def __init__(self):
        self.registered = None
        self.events = []

    def init_problem(self, problem_id):
        assert problem_id == "problem-1"
        assert self.registered is not None
        self.events.append("init_problem")
        return "desc", "instructions", ["get_metrics"]

    def register_agent(self, agent):
        self.registered = agent
        self.events.append("register_agent")


def test_initialize_aiopslab_problem_uses_confirmed_contract():
    agent = AIOpsLabPolicyAgent()
    orchestrator = FakeOrchestrator()

    context = initialize_aiopslab_problem(orchestrator, problem_id="problem-1", agent=agent)

    assert context == ("desc", "instructions", ["get_metrics"])
    assert orchestrator.registered is agent
    assert orchestrator.events == ["register_agent", "init_problem"]
    assert agent.problem_desc == "desc"


def test_aiopslab_policy_agent_returns_parser_compliant_action():
    agent = AIOpsLabPolicyAgent()
    state = json.dumps(
        {
            "timestamp": 1,
            "nodes": [{"node_id": "n1", "cpu_util": 0.9, "mem_util": 0.8, "disk_util": 0.2, "net_util": 0.1}],
            "tasks": [{"task_id": "t1", "node_id": "n1"}],
            "p_fail_scores": {"n1": 0.91},
            "demand_projection": {"n1": 0.8},
            "queue_length": 10,
            "energy_price": 0.1,
        }
    )

    response = asyncio.run(agent.get_action(state))

    assert '"agent": "AgentA"' in response
    assert '"kind": "replicate"' in response
    assert '"target": "n1"' in response
    assert response.count("```") == 2
    assert 'exec_shell("kubectl get pods --all-namespaces")' in response


def test_aiopslab_policy_agent_accepts_instruction_text():
    agent = AIOpsLabPolicyAgent()

    response = asyncio.run(agent.get_action("Please take the next action"))

    assert response.count("```") == 2
    assert 'exec_shell("kubectl get pods --all-namespaces")' in response


def test_aiopslab_policy_agent_submits_no_after_text_observation():
    agent = AIOpsLabPolicyAgent()

    asyncio.run(agent.get_action("Please take the next action"))
    response = asyncio.run(agent.get_action("pod list output"))

    assert response == 'Detection answer: No\n```\nsubmit("No")\n```'


def test_aiopslab_policy_agent_can_submit_yes_for_fault_detection():
    agent = AIOpsLabPolicyAgent(detection_answer="Yes")

    asyncio.run(agent.get_action("Please take the next action"))
    response = asyncio.run(agent.get_action("pod list output"))

    assert response == 'Detection answer: Yes\n```\nsubmit("Yes")\n```'


def test_aiopslab_policy_agent_can_submit_localization_payload():
    agent = AIOpsLabPolicyAgent(submission_code='submit(["geo"])')

    asyncio.run(agent.get_action("Please take the next action"))
    response = asyncio.run(agent.get_action("pod list output"))

    assert response == 'Configured task submission.\n```\nsubmit(["geo"])\n```'


def test_aiopslab_policy_agent_runs_pre_submit_command_before_submit():
    agent = AIOpsLabPolicyAgent(
        submission_code="submit()",
        pre_submit_commands=["kubectl rollout restart deployment/geo -n test-hotel-reservation"],
    )

    asyncio.run(agent.get_action("Please take the next action"))
    command = asyncio.run(agent.get_action("pod list output"))
    final = asyncio.run(agent.get_action("rollout restarted"))

    assert 'exec_shell("kubectl rollout restart deployment/geo -n test-hotel-reservation")' in command
    assert final == "Configured task submission.\n```\nsubmit()\n```"


def test_aiopslab_policy_agent_can_execute_pre_submit_locally(tmp_path):
    marker = tmp_path / "marker"
    agent = AIOpsLabPolicyAgent(
        submission_code="submit()",
        pre_submit_commands=[f"printf done > {marker}"],
        execute_pre_submit_locally=True,
    )

    asyncio.run(agent.get_action("Please take the next action"))
    response = asyncio.run(agent.get_action("pod list output"))

    assert marker.read_text(encoding="utf-8") == "done"
    assert response == "Local pre-submit remediation completed.\n```\nsubmit()\n```"
