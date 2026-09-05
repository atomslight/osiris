import subprocess

from livekit.agents import RunContext, function_tool


@function_tool()
async def shutdown_pc(context: RunContext) -> str:
    """Force shutdown Windows immediately."""
    context.disallow_interruptions()

    await context.session.say("Shutting down the computer now.")
    
    subprocess.Popen(
        ["shutdown", "/s", "/f", "/t", "0"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    return "Computer shutdown initiated."
