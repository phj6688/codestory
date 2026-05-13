# codestory

*Turn any codebase into an animated book of workflows.*

![codestory marquee](docs/images/marquee.gif)

## Install

```
claude-code plugin install codestory
```

## Use

In any repo:

```
/codestory
```

Open the resulting `codestory.html` in a browser.

## Themes

| cococream | dark | minimal | nothing-design |
|---|---|---|---|
| ![cococream](docs/images/theme-cococream.png) | ![dark](docs/images/theme-dark.png) | ![minimal](docs/images/theme-minimal.png) | ![nothing-design](docs/images/theme-nothing-design.png) |

Pick a theme:

```
/codestory theme dark
```

## See it on real code

- [medchat](examples/medchat/) — the gold-standard flow visualisation
- [fastapi-starter](examples/fastapi-starter/) — a small FastAPI app
- [nextjs-starter](examples/nextjs-starter/) — a small Next.js app
- [django-celery](examples/django-celery/) — Django plus async tasks

## How it works

codestory reads a repo, runs scripted discovery on the code (entry points, route handlers, side-effect calls), emits a typed JSON `flows.json`, and renders a single self-contained HTML file. Every flow step cites `file:line`. Unknowns are marked, not invented. Read more in [docs/DISCOVERY.md](docs/DISCOVERY.md).

## Contribute

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## Credits

- Flow-visualisation pattern derived from the `medchat` source artefact.
- `nothing-design` theme inspired by the Nothing design language skill.

## License

MIT — see [LICENSE](LICENSE).
