0. build and start devcontainer
1. connect to the container `./dev`
2. start opencode and login with copilot (`/connect`)
3. restart opencode
4. make sure you are in build agent (press tab), select opus-4.6 (/models) and enable thinking (ctrl+t)
5. start with brainstorm-ump skill (/skills), for example: `/brainstorm-ump Let's create pacman TUI client. Specs for client are in docs/specs`. Answer questions, then **agree to write plan using ralphex-plan skill when brainstorming is complete*.
6. Proceed with ralphex-plan skill to create the plan file. **do not start implementation when plan is generated, just let it save the file**.
7. Now we already have good context in the agent and it's good time to create AGENTS.md so that new sessions have initial context. Run `/init`
8. Commit all changes and start new branch before we start using ralphex.
9. If you are low on copilot premium requests change the model to Sonnet 4.6 and enable thinking in build agent. Otherwise it's better to keep running Opus 4.6 thinking.
10. Quit opencode 
11. Start ralphex and let it cook `ralphex --serve`. Keep cli process running. You can watch the progress in web interface too: http://localhost:8080
12. Once ralphex is done, you can try running your application by pointing it to pacman server hostname.

Error scenarios:
`error: runner: pre-codex review loop: review failed (FAILED signal received)` - the feature is done and reviewed, only external review by another model have not completed. You can either check the result or run external review again: `ralphex --external-only`