#!/usr/bin/env python3

import json
import requests
import subprocess
import re
import time
import psutil
import os


# get the config json file
def load_config():
    try:
        with open("celery_service_name.json", "r") as f:
            config = json.load(f)
        print(f"This is the config file: {config}")
        return config
    except FileNotFoundError:
        raise Exception(
            f"Config file <celery_service_name.json> not found, please create one and proceed! "
        )


CONFIG = load_config()

SETUP = CONFIG.get("setup", None)

if not SETUP:
    raise Exception(
        "The setup key is missing in the config file, please add it and proceed!"
    )

SLACK_WEBHOOK_URL = SETUP.get("slack_webhook_url", "Somewebhook")


def send_slack_alert(message):
    request_payload = {"text": message}
    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(
            SLACK_WEBHOOK_URL, json=request_payload, headers=headers
        )
        response.raise_for_status()
        print("This is the response from Slack:", response.text)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending Slack alert: {e}")


def get_all_running_celery_workers_processes():
    workers = []
    celery_service_name = os.getenv("celery")
    print(f"This is the celery service name: {celery_service_name}")
    for proc in psutil.process_iter(["pid", "cmdline"]):
        cmdline = proc.info["cmdline"]
        whole_command = " ".join(cmdline) if cmdline else ""
        if cmdline and "celery" in whole_command:
            workers.append(" ".join(cmdline))
            print(f"This is the worker command: {' '.join(cmdline)}")
    return workers


def extract_queue_name(log_line):
    match = re.search(r"-Q\s+(\w+)", log_line)
    if match:
        return match.group(1)
    return "celery"


def get_all_systemd_celery_workers():
    workers = {}
    try:
        result = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--all"],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = result.stdout.splitlines()
        for line in lines:
            if "celery" in line:
                fields = line.split()
                if len(fields) > 2:
                    service_name = fields[0]
                    service_status = fields[2]
                    if service_name == "●":
                        service_name = fields[1]
                        service_status = fields[3]
                    workers[service_name] = service_status
        print("systemctl celery workers: ", workers)
    except subprocess.CalledProcessError as e:
        print(f"Error running systemctl: {e}")
    return workers


def ping_celery_worker(worker_name):
    print(f"This is the worker name: {worker_name}")
    if worker_name == "celery":
        # get the hostname of the worker
        hostname = subprocess.run(
            ["hostname"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        worker_name = hostname
    project_work_dir = SETUP.get("project_wd", None)
    if not project_work_dir:
        raise Exception(
            "The project_wd key is missing in the config file, please add it and proceed!"
        )
    project_name = SETUP.get("project_name", None)
    if not project_name:
        raise Exception(
            "The project_name key is missing in the config file, please add it and proceed!"
        )

    try:
        result = subprocess.run(
            [
                "bash",
                "-c",
                f"cd {project_work_dir} && {project_work_dir}/venv/bin/python3 -m celery -A {project_name}.celery inspect ping -d celery@{worker_name}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        output = result.stdout
        print(f"Ping Output: {output}")
        return worker_name in output
    except subprocess.CalledProcessError as e:
        print(f"Error executing ping command: {e}")
        return False


def is_worker_alive(worker_cmd):
    for proc in psutil.process_iter(["pid", "cmdline"]):
        if " ".join(proc.info["cmdline"]) == worker_cmd:
            return True
    return False


def restart_worker(celery_name, systemd=False):
    print(f"Restarting Celery Worker: {celery_name}")
    send_slack_alert(f"⚠️ Celery Worker **{celery_name}** is down! Restarting now...")
    # open the json file

    # get systemd service name
    if not systemd:
        celery_name = CONFIG.get(celery_name, None)
    try:
        subprocess.run(["systemctl", "restart", celery_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error restarting worker: {e}")


def monitor():
    while True:
        # get from pid
        workers = get_all_running_celery_workers_processes()

        if not workers:
            print("No Celery workers found! Check the server.")
            send_slack_alert(
                "🚨 No Celery workers are running! Immediate attention required."
            )
        else:
            for worker_cmd in workers:
                celery_name = extract_queue_name(worker_cmd)
                is_alive = ping_celery_worker(celery_name)
                print(f"Checking if the worker is alive: {is_alive}")
                if not is_alive:
                    send_slack_alert(
                        f"⚠️ Celery Worker **{worker_cmd}** is down! Restarting now..."
                    )
                    restart_worker(celery_name)
        # get from systemd
        systemd_workers = get_all_systemd_celery_workers()
        for worker_name, worker_status in systemd_workers.items():
            print(f"Systemds worker name: {worker_name} and status: {worker_status}")
            if worker_status != "active":
                send_slack_alert(
                    f"⚠️ Celery Worker **{worker_name}** is down! Restarting now..."
                )
                restart_worker(worker_name, systemd=True)

        time.sleep(20)


if __name__ == "__main__":
    print("Starting Celery Worker Monitoring...")
    monitor()
