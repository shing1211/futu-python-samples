# Futu Python Samples

Standalone Python examples using the [Futu OpenAPI](https://openapi.futunn.com/) SDK.

## Structure

```
futu-python-samples/
├── examples/
│   ├── README.md          # Example descriptions & index
│   ├── 00_connect_ha/     # HA gateway connection with TCP probe + RSA
│   └── ...
└── README.md
```

## Quick Start

```bash
# Install futu-api
pip install futu-api

# Run an example
python examples/00_connect_ha/main.py
```

## Environment

| Variable | Description | Default |
|----------|-------------|---------|
| `FUTU_ADDR` | OpenD server address | `127.0.0.1:11111` |

## Remote OpenD (RSA Encryption)

For remote OpenD instances with RSA encryption enabled, the RSA private key is read from:

```
/etc/futu/keys/private_key.pem   # PKCS#1 format, 1024-bit
```

Each example configures `SysConfig` before connecting. See `examples/00_connect_ha/` for the HA connection pattern.
