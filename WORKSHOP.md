1. Build and start devcontainer. `>reopen in container` in VS code.
2. Open terminal(WSL) and connect to the container: `./dev`. Forget about IDE here, use termial full screen.
3. Start `opencode` and log in with GitHub Copilot (`/connect`).
4. Select Opus 4.6 model (`/models`). Turn on thinking (ctrl+t).
5. Start with the ralphex-plan skill (`/skills`), for example: `/raplphex-plan Let's create a plan to implement multiplayer pacman client. Client specs are in docs/specs`. 
6. Answer ralphex-plan questions to create the plan file. Do not start implementation after the plan is generated; just let it save the plan file.
7. Now we already have good context in the agent, and it's a good time to create AGENTS.md so that new sessions have initial context. Run `/init`.
8. Quit open code `/exit`
9. Commit to a new branch `git checkout -b <creative-branch-name> && git commit -am "plan"`
10. Start ralphex and let it cook: `ralphex --serve`. Watch in the terminal or at https://127.0.0.1:8080.
11. Once ralphex is done, we are ready to play! Check `README.md` or ask `opencode` _"how to launch the app with server host `pacman-server.mschedrin.workers.dev`"_