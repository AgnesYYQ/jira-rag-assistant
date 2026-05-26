from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END

# 1. 定义我们之前聊到的状态字典 (State)
class AgentState(TypedDict):
    issue_desc: str       # Jira 传入的报错描述
    retrieved_docs: list  # RAG 捞出来的参考文档
    ai_response: str      # 大模型生成的草稿建议
    grade: str            # 评估结果：'pass' 或 'fail'

# --- 定义节点 (Nodes) ---
def retrieve_node(state: AgentState):
    # 这里放你原本代码里 AmazonKnowledgeBasesRetriever 的逻辑
    docs = retriever.get_relevant_documents(state["issue_desc"])
    return {"retrieved_docs": docs}

def generate_node(state: AgentState):
    # 这里放你原本代码里调用 Bedrock 组合 Prompt 生成回答的逻辑
    response = bedrock_llm.invoke(state["issue_desc"], state["retrieved_docs"])
    return {"ai_response": response}

def evaluate_node(state: AgentState):
    # 【这就是新增的评估机制！】
    # 用一个轻量、判定能力强的 Prompt，让大模型当裁判，给刚才的回答打分
    eval_prompt = f"问题: {state['issue_desc']}\nAI回答: {state['ai_response']}\n请判断回答是否切中要害且有参考价值？回答 YES 或 NO。"
    score = evaluator_llm.invoke(eval_prompt)
    
    grade = "pass" if "YES" in score.upper() else "fail"
    return {"grade": grade}

# --- 定义条件边逻辑 (Conditional Edge) ---
def decide_next_step(state: AgentState) -> Literal["post_comment", "re_retrieve"]:
    if state["grade"] == "pass":
        return "post_comment"  # 及格了，走发布路径
    else:
        return "re_retrieve"   # 不及格，重新去检索（或者走人工介入、或者降低检索门槛）

# --- 组装流程图 ---
workflow = StateGraph(AgentState)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("generate", generate_node)
workflow.add_node("evaluate", evaluate_node)
workflow.add_node("post_comment", lambda state: print("真正发布到Jira:", state["ai_response"]))

# 连线
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", "evaluate")

# 核心：根据评估节点的 grade 字典字段，动态决定分叉路
workflow.add_conditional_edges(
    "evaluate",
    decide_next_step,
    {
        "post_comment": "post_comment",
        "re_retrieve": "retrieve" # 循环回去，实现自我修正 (Self-RAG)
    }
)
workflow.add_edge("post_comment", END)
app = workflow.compile()
