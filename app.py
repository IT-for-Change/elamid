from flask import Flask, request, Response
import docker
from docker.errors import DockerException, ImageNotFound, ContainerError, NotFound
import json
from loguru import logger

app = Flask(__name__)

logger.add("/workspace/elamid.log", level="DEBUG",
           rotation="10 MB", compression="zip")


class ElamidError(Exception):
    def __init__(self, message, original_exception):
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)


@app.route("/run", methods=["GET"])
def run():
    logger.info('Starting /run')
    image_name = request.args.get("ela_image")
    ela_api_host = request.args.get("ela_api_host")
    ela_api_port = request.args.get("ela_api_port")
    ela_get_api = request.args.get("ela_get_api")
    ela_put_api = request.args.get("ela_put_api")
    ela_add_file_api = request.args.get("ela_add_file_api")
    ela_api_token = request.args.get("ela_api_token")
    ela_ai_install_dir = request.args.get("ela_ai_install_dir")
    ela_ai_operation = request.args.get("ela_ai_operation")
    ela_activity = request.args.get("ela_activity")

    container_env_config = {
        "ela_api_host": ela_api_host,
        "ela_api_port": ela_api_port,
        "ela_get_api": ela_get_api,
        "ela_put_api": ela_put_api,
        "ela_add_file_api": ela_add_file_api,
        "ela_api_token": ela_api_token,
        "ela_ai_install_dir": ela_ai_install_dir,
        "ela_ai_operation": ela_ai_operation
    }

    environment = {
        "APP_CONFIG": json.dumps(container_env_config)
    }

    # command = f"/apps/{ela_ai_operation}/app.py"
    volumes = {
        f'{ela_ai_install_dir}/apps': {'bind': '/apps', 'mode': 'rw'}
    }
    command = f'-m {ela_ai_operation}.app {ela_activity}'
    # command = f'app.py {ela_activity}'
    working_dir = '/apps'
    network = 'host'

    try:
        try:
            logger.info('Creating docker client')
            # Explicitly use Docker unix socket
            client = docker.DockerClient(
                base_url="unix:///var/run/docker.sock")
        except Exception as e:
            raise ElamidError(f"Unable to create elamid client", e)

        try:
            client.images.get(image_name)
        except ImageNotFound:
            raise ElamidError(f"Unable to find image {image_name}")

        try:
            container_name = 'myelaai'
            try:
                logger.info(f'Getting container {container_name}')
                container = client.containers.get(container_name)
                if container.status == "running":
                    logger.info(
                        f"Container {container.name} is alreay running. Stopping now...")
                    container.stop()  # Sends SIGTERM, waits 10s, then SIGKILL

                # Remove the container
                container.remove(force=True)
                logger.info(
                    f"Container {container.name} removed successfully.")
            except NotFound:
                pass

            logger.info('Running new container')
            container = client.containers.run(
                image_name,
                working_dir=working_dir,
                command=command,
                volumes=volumes,
                network=network,
                environment=environment,
                detach=True,
                name=container_name,
                remove=True,
                stderr=True,
                stdout=True
            )
            logger.info(f'Container {container_name} started successfully')

        except Exception as e:
            msg = f"Unable to run container {container_name} for image {image_name} with command: {command}."
            logger.error(msg)
            raise ElamidError(msg)

        return Response("Assessment started successfully. Use the refresh button to check progress",
                        status=200,
                        mimetype="text/plain")

    except ElamidError as e:
        return Response(f"Elamid error: {str(e.message)}. {e.original_exception}",
                        status=500,
                        mimetype="text/plain")
    except DockerException as e:
        return Response(f"Elamid docker error: {str(e.message)}",
                        status=500,
                        mimetype="text/plain")
    except Exception as e:
        return Response(f"Unknown elamid error: {str(e.message)}",
                        status=500,
                        mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
