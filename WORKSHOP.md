0. build and start devcontainer
1. connect to the container `./dev`
2. start opencode and login with copilot (`/connect`)
3. restart opencode
4. make sure you are in build agent (press tab), select opus-4.6 (/models) and enable thinking (ctrl+t)
5. ~~do the same for plan agent~~
6. start with brainstorm-ump skill (/skills), for example: `/brainstorm-ump Let's create pacman TUI client. Specs for client are in docs/specs`. Answer questions, then **agree to write plan using ralphex-plan skill when brainstorming is complete*.
7. Proceed with ralphex-plan skill to create the plan file. **do not start implementation when plan is generated, just let it save the file**.
8. Now we already have good context in the agent and it's good time to create AGENTS.md so that new sessions have initial context. Run `/init`
9. Commit all changes before we start using ralphex.
10. change the model to gpt-5.3-codex for build and plan agent. 
11. Start ralphex and let it cook `ralphex --serve`
