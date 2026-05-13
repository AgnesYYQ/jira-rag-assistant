def main():
    """
    Manual CLI entry point for JiraBot: generates and posts a comment to a JIRA ticket.

    Note: In production, the agent is triggered automatically by Jira webhooks via the webhook server.
    This script is for manual/testing use only and does not interfere with the webhook flow.
    """
import argparse
from .agent import get_bedrock_client, get_retriever, get_jira_toolkit, get_system_prompt

"""
JiraBot main entry point: generates and posts a comment to a JIRA ticket.

This module serves two purposes:
1. Manual CLI/testing: Run directly for local/manual comment generation and posting.
2. Automation: Called by the webhook server to process new Jira tickets automatically.

In production, the webhook server triggers this logic for new tickets. Manual CLI runs are for development/testing.
"""
import argparse
from .agent import get_bedrock_client, get_retriever, get_jira_toolkit, get_system_prompt

def main():
    parser = argparse.ArgumentParser(description="JiraBot (manual): Generate and post JIRA comments using Bedrock RAG.")
    parser.add_argument('--ticket', required=True, help='JIRA ticket key (e.g., ABC-123)')
    parser.add_argument('--dry-run', action='store_true', help='Only print the comment, do not post')
    args = parser.parse_args()

    bedrock_client = get_bedrock_client()
    retriever = get_retriever()
    jira_toolkit = get_jira_toolkit()
    system_prompt = get_system_prompt()

    # Shared logic: retrieve context and generate comment for the specified ticket
    # (Used by both manual CLI and webhook-triggered runs)
    user_query = f"What should I comment on ticket {args.ticket}?"
    response = bedrock_client.retrieve_and_generate(
        input={'text': user_query},
        retrieveAndGenerateConfiguration={
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': retriever.knowledge_base_id,
                'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0'
            }
        }
    )
    comment = response['output']['text']
    print(f"Generated comment:\n{comment}\n")

    if not args.dry_run:
        jira_toolkit.get_tools()[0].add_comment(args.ticket, comment)
        print(f"Comment posted to {args.ticket}")
    else:
        print("Dry run: comment not posted.")

if __name__ == "__main__":
    main()
