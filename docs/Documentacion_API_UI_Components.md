# API Documentation — UI Components

This bundle documents the following GUI classes used in the desktop workflow:

- `SquareWidget`
- `InitAPP`
- `RunConfigurationApp`
- `LauncherApp`

## Workflow relationship

The current desktop UI pipeline is:

```text
InitAPP
  -> RunConfigurationApp
      -> SessionManager / PreExperimentManager
          -> LauncherApp
              + auxiliary SquareWidget overlays
```

### Roles

- **`InitAPP`**: collects base metadata and root path.
- **`RunConfigurationApp`**: refines experiment-level parameters and instantiates the manager.
- **`LauncherApp`**: operator-facing execution control panel.
- **`SquareWidget`**: floating visual overlays used by managers.

See the individual files for the API-level details of each component.
