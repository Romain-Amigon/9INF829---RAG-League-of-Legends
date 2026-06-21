import sys
import json
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langchain_mcp_adapters.tools import load_mcp_tools

OPGG_URL = "https://mcp-api.op.gg/mcp"


async def describe_tools():
    try:
        async with streamablehttp_client(OPGG_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
                for t in tools:
                    print(f"=== {t.name} ===")
                    print(t.description)
                    print(json.dumps(t.args, ensure_ascii=False, indent=2))
                    print()
    except Exception as e:
        print(f"Erreur d'exécution OP.GG : {e}")


async def fetch_opgg(tool_name: str, arguments: dict):
    """
    Se connecte à OP.GG, invoque l'outil demandé avec les arguments fournis,
    et ne print QUE le résultat (ou l'erreur) pour capture par l'Agent principal.
    """
    try:
        async with streamablehttp_client(OPGG_URL) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)

                tool = next((t for t in tools if t.name == tool_name), None)

                if not tool:
                    print(f"Erreur: Outil OP.GG '{tool_name}' introuvable sur le serveur distant.")
                    return

                result = await tool.ainvoke(arguments)

                if isinstance(result, list) and len(result) > 0 and 'text' in result[0]:
                    print(result[0]['text'])
                else:
                    print(str(result))

    except Exception as e:
        print(f"Erreur d'exécution OP.GG : {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--describe":
        asyncio.run(describe_tools())
    else:
        tool_arg = sys.argv[1] if len(sys.argv) > 1 else "lol_get_champion_analysis"
        try:
            args_arg = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        except json.JSONDecodeError:
            args_arg = {}
        asyncio.run(fetch_opgg(tool_arg, args_arg))