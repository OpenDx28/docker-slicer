# docker-slicer

This repository holds a Docker image configured to run the 3D Slicer application in a VNC server compatible with 3D acceleration using Nvidia GPUs.

## Instructions

Build the image locally:

```bash
cd src
docker build -t slicer . 
```

Run the image locally:

```bash
docker run --rm -it --gpus all --shm-size=512m -p 6901:6901 -e VNC_DISABLE_AUTH=true --user root slicer
```

## Configuration

Available environment variables:

| Variable                                  | Description                                                                                   | Default     |
|-------------------------------------------|-----------------------------------------------------------------------------------------------|-------------|
| VNC_DISABLE_AUTH                          | Disable VNC authentication (no user/password required, use with caution)                      | false       |
| VNC_PW                                    | Password for the basic auth (the user is always: "user")                                      | vncpassword |
| VNC_PORT                                  | VNC port                                                                                      | 6901        |
| VNC_ALLOW_CLIENT_TO_OVERRIDE_VNC_SETTINGS | Enable/disable the client to override the VNC settings, it does not have effect on the web UI | false       |

## Deployment

To deploy the application to a Kubernetes cluster:

```bash
cd k8s
kubectl apply -k .     
```
