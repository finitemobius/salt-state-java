# salt-state-java
[Salt](https://github.com/saltstack/salt) states to manage [Java](http://www.oracle.com/technetwork/java/index.html) configuration on Linux
## Installation
Install `java.py` as described in the [SaltStack documentation](https://docs.saltstack.com/en/latest/ref/modules/#modules-are-easy-to-write). This typically means placing the file under `/srv/salt/_states/` and running `saltutil.sync_states`.
## trust_cert
This state module enforces the inclusion of a trusted certificate authority in Java's trust store.

This module aims to be distribution-agnostic. It attempts to identify `$JAVA_HOME` if the user doesn't explicity provide it.
### Usage
First, deploy the internal CA's public certificate using `file.managed`.

Create an SLS file similar to the following:
```yaml
Java certificate install:
  java.trust_cert:
    - cert_file: /etc/ssl/certs/internal_CA.pem
    - alias: internal_CA
```
The parameters that `trust_cert` takes are:
* `name`: not used
* `cert_file`: Full path of the public certificate of the CA. This must exist on the minion, ideally via `file.managed`. Required.
* `alias`: Alias to use when storing in the trust store. Java uses this to reference the certificate. Required.
* `storepass`: Trust store password. Optional; defaults to `changeit`, which is Java's default.
* `java_home`: Explicitly define `$JAVA_HOME`. Optional; defaults to sourcing `/etc/profile` to determine location.
