from flask import Flask, request, Response
import docker
from docker.errors import DockerException, ImageNotFound, ContainerError, NotFound

app = Flask(__name__)


class ElamidError(Exception):
    def __init__(self, message, original_exception):
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)


@app.route("/run", methods=["GET"])
def run():
    image_name = request.args.get("ela_image")
    ela_host = request.args.get("ela_api_host")
    ela_port = request.args.get("ela_api_port")
    ela_api = request.args.get("ela_api")
    ela_activity = request.args.get("ela_activity")
    ela_ai_install_dir = request.args.get("ela_ai_install_dir")
    ela_ai_operation = request.args.get("ela_ai_operation")

    command = f"/apps/{ela_ai_operation}/app.py {ela_host} {ela_port} {ela_api} {ela_activity}"
    volumes = {
        f'{ela_ai_install_dir}/apps': {'bind': '/apps', 'mode': 'rw'}
    }
    network = 'host'

    APP_ENV = ''
    if ela_ai_operation in ["lang_check", "stt"]:
        APP_ENV = "whisper"
    elif ela_ai_operation == "sdz":
        APP_ENV = "pyannote"
    elif ela_ai_operation == "nlp":
        APP_ENV = "spacy"
    elif ela_ai_operation == "report":
        APP_ENV = "report"

    environment = {
        "APP_ENV": APP_ENV
    }

    try:
        try:
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
                container = client.containers.get(container_name)
                if container.status == "running":
                    print(f"Stopping container {container.name}...")
                    container.stop()  # Sends SIGTERM, waits 10s, then SIGKILL

                # Remove the container
                container.remove(force=True)
                print(f"Container {container.name} removed successfully.")
            except NotFound:
                pass

            container = client.containers.run(
                image_name,
                command,
                volumes=volumes,
                network=network,
                environment=environment,
                detach=True,
                name=container_name,
                remove=True,
                stderr=True,
                stdout=True
            )
        except Exception as e:
            raise ElamidError(
                f"Unable to run container {container_name} for image {image_name} with command: {command}.")

        return Response("Assessment started successfully",
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
