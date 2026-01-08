from __future__ import annotations

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.llm.prompts import ANSWER_HUMAN_TEMPLATE, ANSWER_SYSTEM_PROMPT, REWRITE_SYSTEM_PROMPT


def build_rewrite_chain(model):
    """history + input -> standalone question (string)."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", REWRITE_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    )
    return prompt | model | StrOutputParser()


def build_answer_chain(model):
    """question + context + style -> final answer (string)."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ANSWER_SYSTEM_PROMPT),
            ("human", ANSWER_HUMAN_TEMPLATE),
        ]
    )
    return prompt | model | StrOutputParser()
