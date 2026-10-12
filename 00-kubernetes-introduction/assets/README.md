# Introduction diagram assets

Nine original diagrams are supplied in two formats:

- PNG: 2400 x 1440 pixels, used by the notebook for portable rendering.
- SVG: editable vector originals, with accessible titles/descriptions and no scripts or external image/font references.

| Prefix | Diagram |
|---|---|
| 01 | [Docker, Compose and Kubernetes](01-docker-compose-kubernetes.png) / [SVG](01-docker-compose-kubernetes.svg) |
| 02 | [Images, registry and runtimes](02-images-and-runtimes.png) / [SVG](02-images-and-runtimes.svg) |
| 03 | [Cluster architecture and components](03-cluster-architecture.png) / [SVG](03-cluster-architecture.svg) |
| 04 | [Containers inside a Pod](04-inside-a-pod.png) / [SVG](04-inside-a-pod.svg) |
| 05 | [Desired state and replacement Pods](05-desired-state.png) / [SVG](05-desired-state.svg) |
| 06 | [Services and access](06-services-and-access.png) / [SVG](06-services-and-access.svg) |
| 07 | [Persistent storage lifecycle](07-storage-lifecycle.png) / [SVG](07-storage-lifecycle.svg) |
| 08 | [Minikube and its two image stores](08-minikube-two-stores.png) / [SVG](08-minikube-two-stores.svg) |
| 09 | [AWS, Azure and Google Cloud options](09-cloud-options.png) / [SVG](09-cloud-options.svg) |

The artwork uses original shapes and text rather than downloaded logos or screenshots. Font files are not included.

For maintainers, edit the introduction's `README.md` and this folder's `render_diagrams.py`, then regenerate the notebook and images together:

```bash
python -m pip install "Pillow>=10.1"
python 00-kubernetes-introduction/assets/render_diagrams.py
```

Run from the workspace root. Pillow is only needed for regeneration; viewing the notebook needs no drawing dependency. The renderer uses an available Segoe UI or DejaVu Sans font with a Pillow fallback. Regeneration does not contact the network or start a cluster.

Keep the PNGs, SVGs, guide and notebook together in version control. Relative image links work without a GitHub-specific URL or an external image host.
