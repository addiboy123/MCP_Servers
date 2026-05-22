import asyncio
import json
import os
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables from the repository root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class MCPGeminiClient:
    """Client for interacting with Google Gemini using MCP tools."""

    def __init__(self, model: str = "gemini-2.5-flash"):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.model = model

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "Google Gemini API key not found. Set GEMINI_API_KEY in your environment."
            )
        self.client = genai.Client(api_key=api_key)

    async def connect_to_server(self, server_script_path: str = "server.py"):
        """Connect to an MCP server."""
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read, write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

        await self.session.initialize()

        tools_result = await self.session.list_tools()
        print("\nConnected to server with tools:")
        for tool in tools_result.tools:
            print(f"  - {tool.name}: {tool.description}")

    async def get_gemini_tools(self) -> list[types.Tool]:
        """Convert MCP tools to Gemini Tool format."""
        tools_result = await self.session.list_tools()
        function_declarations = [
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=tool.inputSchema,
            )
            for tool in tools_result.tools
        ]
        return [types.Tool(function_declarations=function_declarations)]

    async def process_query(self, query: str) -> str:
        """Process a query using Gemini, handling MCP tool calls in a loop."""
        tools = await self.get_gemini_tools()
        contents: list[types.Content] = [
            types.Content(role="user", parts=[types.Part(text=query)])
        ]

        while True:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(tools=tools),
            )

            candidate = response.candidates[0]
            contents.append(candidate.content)  # Add assistant turn to history

            # Collect any tool calls in this response
            tool_calls = [
                part for part in candidate.content.parts if part.function_call
            ]

            if not tool_calls:
                # No tool calls — return the final text response
                return response.text

            # Execute all tool calls and collect results
            tool_results = []
            for part in tool_calls:
                fc = part.function_call
                print(f"\n[Tool call] {fc.name}({dict(fc.args)})")

                mcp_result = await self.session.call_tool(fc.name, arguments=dict(fc.args))
                result_text = "\n".join(
                    c.text for c in mcp_result.content if hasattr(c, "text")
                )
                print(f"[Tool result] {result_text[:200]}")

                tool_results.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": result_text},
                        )
                    )
                )

            # Feed tool results back to the model
            contents.append(types.Content(role="tool", parts=tool_results))

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


async def main():
    client = MCPGeminiClient()
    try:
        await client.connect_to_server("server.py")

        query = "What is our company's vacation policy?"
        print(f"\nQuery: {query}")

        response = await client.process_query(query)
        print(f"\nResponse: {response}")
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())