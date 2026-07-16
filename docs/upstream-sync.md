# Upstream-Änderungen kontrolliert übernehmen

Das private Repository ist eine eigenständige Kopie mit erhaltener Historie, kein
GitHub-Fork. `origin` zeigt auf `Skrockle/Essentia-Studio`; `upstream` bleibt das
öffentliche Analyseprojekt.

```bash
git fetch upstream
git switch -c review/upstream-YYYY-MM-DD main
git log --oneline main..upstream/main
git diff --stat main...upstream/main
```

Relevante Commits werden einzeln per `git cherry-pick <sha>` oder nach manueller
Portierung übernommen. Danach immer `python scripts/verify.py` und die Browserflows
ausführen. Die Review-Branch wird erst nach Prüfung gemergt. Kein Force-Push auf
`main`, und niemals die Push-URL von `upstream` auf das private Repository setzen.

Der Playlist-Upstream ist in
`vendor/navidrome-smart-playlist-generator/UPSTREAM.md` mit exaktem Commit
dokumentiert und wird auf dieselbe Weise separat verglichen.
