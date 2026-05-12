# futu-python-samples AGENTS.md

## Project

Python examples for Futu OpenAPI. Each example is a standalone script demonstrating one SDK function.

## Dev Commands

```bash
python examples/00_connect_ha/main.py   # Run an example
```

## Environment

| Variable | Description | Default |
|----------|-------------|---------|
| `FUTU_ADDR` | OpenD server address | `127.0.0.1:11111` |

## RSA Key

RSA private key for remote OpenD connections:

```
/etc/futu/keys/private_key.pem   # PKCS#1 format, 1024-bit
```

## SDK Notes

- SDK: `futu-api` (pip install)
- Docs: https://openapi.futunn.com/futu-api-doc/
- `SysConfig.enable_proto_encrypt()` + `SysConfig.set_init_rsa_file()` must be called BEFORE `OpenQuoteContext()` when connecting to remote OpenD with RSA
- `is_encrypt()` in SDK has **no localhost vs remote distinction** — RSA is purely client-side opt-in based on global `SysConfig.IS_PROTO_ENCRYPT` flag
- Best practice: per-host `is_rsa` flag with fallback retry
