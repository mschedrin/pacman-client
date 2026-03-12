1. Build and start devcontainer. `>reopen in container` in VS code.
2. Open terminal(WSL) and connect to the container: `./dev`. Forget about IDE here, use termial full screen.
3. Start `opencode` and log in with GitHub Copilot (`/connect`).
4. Select Opus 4.6 model (`/models`). Turn on thinking (ctrl+t).
5. Design your client with brainstorm-ump skill (`/skills`). For example: `/brainstorm-ump Let's design implementation multiplayer pacman client. Specs are in docs/specs`. When complete select _Write plan (Create docs/plans/YYYY-MM-DD-<topic>.md with implementation steps using ralphex-plan skill )_
6. Conversation will be taken over by ralphex-plan skill. If this did not work, you can manually start ralphex-plan skill (`/skills`), for example: `/raplphex-plan Let's create a plan to implement multiplayer pacman client. Client specs are in docs/specs`. 
7. Answer ralphex-plan questions to create the plan file. **Do not start implementation after the plan is generated; just let it save the plan file**
8. Now we already have good context in the agent, and it's a good time to create AGENTS.md so that new sessions have initial context. Run `/init`.
9. Quit open code `/exit`
10. Commit to a new branch `git checkout -b <creative-branch-name> && git commit -am "plan"`
11. Start ralphex and let it cook: `ralphex --serve`. Watch in the terminal or at https://127.0.0.1:8080.
12. Once ralphex is done, we are ready to play! Check `README.md` or ask `opencode` _"how to launch the app with server host `pacman-server.mschedrin.workers.dev`"_