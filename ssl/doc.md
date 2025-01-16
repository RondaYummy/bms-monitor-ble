Generate SSL sertificates in folder ./ssl

```bash
openssl req -x509 -newkey rsa:2048 -keyout server.key -out server.crt -days 365 -nodes
```
Вкажіть IP-адресу Raspberry Pi як "Common Name" (CN), наприклад: 192.168.1.100.
