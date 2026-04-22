# Below Worker Install

1. Sync this repo to Below and confirm `python -m core.cluster.below.queue_schema --self-test` prints `OK`.
2. Ensure `.buildrunner/research-queue/` exists in the Below checkout.
3. Confirm Below can reach local Ollama and Jimmy SSH with the cluster config in `~/.buildrunner/cluster.json`.
4. Confirm Jimmy has `.venv/bin/python` in `/home/byronhudson/repos/BuildRunner3`.
5. For WSL2 or Linux, copy `core/cluster/below/below_worker.service` to `/etc/systemd/system/`.
6. Edit `WorkingDirectory=` if the Below checkout path differs.
7. Create the log file with `sudo touch /var/log/br3-below-worker.log`.
8. Set ownership so the service user can append to the log.
9. Run `sudo systemctl daemon-reload`.
10. Run `sudo systemctl enable --now below_worker.service` or rename to `br3-below-worker.service` per host policy.
11. Check logs with `tail -f /var/log/br3-below-worker.log`.
12. For native Windows, import `core/cluster/below/below_worker_scheduler.xml` in Task Scheduler.
13. Update the `<WorkingDirectory>` path if the checkout is elsewhere.
14. Ensure `python.exe` resolves in the scheduled task environment.
15. The task writes logs to `%USERPROFILE%\AppData\Local\BR3\below-worker.log`.
16. Start the task once manually to verify queue creation and Ollama reachability.
17. Drop a JSONL record into `pending.jsonl` and wait for `completed.jsonl`.
18. Successful records commit to Jimmy, push to `muddy`, and trigger research reindex.
19. SIGTERM drains the current record before the worker exits.
20. If reindex times out, the completed record stays `ok` with a warning.
