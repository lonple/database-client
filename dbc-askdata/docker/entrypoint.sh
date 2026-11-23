#!/bin/sh
set -eu

# Gateway 经 Nacos lb://dbc-askdata 调本服务：必须登记容器网 IP，不能是 127.0.0.1
if [ -z "${DBC_ASKDATA_NACOS_IP:-}" ]; then
  IP="$(hostname -i 2>/dev/null | awk '{print $1}')"
  if [ -n "${IP}" ] && [ "${IP}" != "127.0.0.1" ]; then
    export DBC_ASKDATA_NACOS_IP="${IP}"
  fi
fi

exec uvicorn dbc_askdata.main:app --host 0.0.0.0 --port 8009
