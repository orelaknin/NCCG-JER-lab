#!/bin/bash

# Variables
PING_CMD="ping -c 1 $HOST"
SSH_CMD="sshpass -p '$PASSWORD' ssh -o StrictHostKeyChecking=no -o BatchMode=yes $USER@$HOST"
REBOOT_CMD="sudo reboot"
WAIT_TIME=30
RETRY_INTERVAL=5  # Time to wait between retry attempts

# Function to check if the host is reachable
is_host_reachable() {
    echo "Pinging $HOST..."
    $PING_CMD > /dev/null 2>&1
    return $?
}

# Function to perform SSH command
perform_ssh_command() {
    local cmd=$1
    echo "Attempting to execute command on $HOST: $cmd"
    echo "$PASSWORD" | sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no -o BatchMode=yes $USER@$HOST "$cmd" > /dev/null 2>&1
    local result=$?
    if [ $result -ne 0 ]; then
        echo "Failed to execute command on $HOST. Exit status: $result"
        return 1
    fi
    return 0
}

# Main loop
while true; do
    if is_host_reachable; then
        echo "$HOST is reachable. Attempting to reboot..."
	sleep 10
        # Send the reboot command
        perform_ssh_command "$REBOOT_CMD"
        sleep 10

        echo "Reboot command sent. Waiting for the host to go down..."
        
        # Wait until the host is down
        while is_host_reachable; do
            echo "$HOST is still reachable. Waiting..."
            sleep $RETRY_INTERVAL
        done

        echo "$HOST is down. Waiting for additional $WAIT_TIME seconds..."
        sleep $WAIT_TIME

        echo "Waiting for $HOST to come back online..."
        
        # Wait until the host is back online
        while ! is_host_reachable; do
            echo "$HOST is still not reachable. Waiting..."
            sleep $RETRY_INTERVAL
        done

        echo "$HOST is back online. Checking if another reboot is needed..."
	sleep 10
        # Optionally, send another reboot command after the host is back online
        perform_ssh_command "$REBOOT_CMD"
        sleep 10


        echo "$HOST has been rebooted again"
        
    else
        echo "$HOST is not reachable. Retrying in 10 seconds..."
        sleep 10
    fi
done
