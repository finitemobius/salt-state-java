#!/usr/bin/env python
import os
import fnmatch
import subprocess


def trust_cert(name, cert_file, alias, storepass='changeit', java_home=None):
    """
    Install a trusted root certificate into the Java trust store.

    The certificate must exist on the minion, i.e., via file.managed

    :param name: Name of the state; should be unique
    :param cert_file: Full path to the public certificate on the minion (required)
    :param alias: Alias to use when storing in the trust store (required)
    :param storepass: Trust store password (optional, defaults to 'changeit')
    :param java_home: Explicitly define JAVA_HOME (optional, defaults to system JAVA_HOME)
    :return:
    """
    # Set up the return object (dict)
    ret = {'name': name, 'changes': {}, 'result': False, 'comment': ''}

    # Define "live" and "test" result codes
    result_code = {  # Live
        'none': True,
        'failure': False,
        'success': True
    }
    if __opts__['test']:  # Test
        result_code['failure'] = None
        result_code['success'] = None

    # If Java is not installed, nothing to do
    java_home = _find_java_home(java_home)
    if not java_home:
        ret['result'] = result_code['none']
        ret['comment'] = 'Java is not installed'
        return ret
    # Enforce the existence of $JAVA_HOME for keytool
    os.putenv(r'JAVA_HOME', java_home)

    # Make sure the trust store exists; error otherwise
    trust_store = _find_trust_store(java_home)
    if not trust_store:
        ret['result'] = result_code['failure']
        ret['comment'] = 'Could not find Java trust store.'
        return ret

    # keytool binary
    keytool = _find_keytool(java_home)
    if not keytool:
        ret['result'] = result_code['failure']
        ret['comment'] = 'Could not find keytool binary.'
        return ret

    # If the alias already exists, nothing to do
    keytool_opts = ['-keystore', trust_store, '-list', '-alias', alias, '-storepass', storepass]
    try:
        subprocess.check_output([keytool] + keytool_opts, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        # The alias does not exist (keep going)
        pass
    else:
        # The alias does exist (do nothing)
        ret['result'] = result_code['none']
        ret['comment'] = 'CA alias exists in trust store.'
        return ret

    # Check to see if the storepass is wrong or the file is corrupt
    # We could skip this and return an error when the cert installation is attempted,
    # but I want to catch this if 'test' is set, too.
    keytool_opts = ['-keystore', trust_store, '-list', '-storepass', storepass]
    try:
        subprocess.check_output([keytool] + keytool_opts, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        # keytool failed to open the keystore for some reason
        ret['result'] = result_code['failure']
        ret['comment'] = 'Keystore ' + trust_store + ' problem:\n' + e.output
        return ret

    # Make sure the certificate file is a valid cert; error otherwise
    keytool_opts = ['-printcert', '-file', cert_file]
    try:
        subprocess.check_output([keytool] + keytool_opts)
    except subprocess.CalledProcessError as e:
        # keytool could not decode the certificate
        ret['result'] = result_code['failure']
        ret['comment'] = 'File ' + cert_file + ' is not a valid certificate:\n' + e.output
        return ret

    # Install the certificate
    if not __opts__['test']:
        keytool_opts = ['-importcert', '-trustcacerts', '-file', cert_file, '-keystore', trust_store,
                        '-alias', alias, '-storepass', storepass, '-noprompt']
        try:
            subprocess.check_output([keytool] + keytool_opts, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            # Upon failure, return the Java exception
            ret['result'] = result_code['failure']
            ret['comment'] = e.output
        else:
            # Success
            ret['result'] = result_code['success']
            ret['comment'] = 'Certificate "{0}" was added as a trusted root.'.format(alias)
            ret['changes'] = {
                'old': '',
                'new': alias
            }
    else:  # __opts__['test']:
        ret['result'] = result_code['success']
        ret['comment'] = 'Certificate "{0}" will be added as a trusted root.'.format(alias)
        ret['changes'] = {
            'old': '',
            'new': alias
        }
    return ret


def _find_trust_store(java_home):
    # Attempt to find the system default trust store
    ret = []
    for root, dirnames, filenames in os.walk(java_home):
        for filename in fnmatch.filter(filenames, 'cacerts'):
            ret.append(os.path.join(root, filename))
    if len(ret) <= 0:
        return None
    return ret[0]


def _find_java_home(java_home):
    # Test the user-defined java_home to see if it is valid
    if java_home:
        # Test to see if this is a directory
        # _find_trust_store() and _find_keytool() will do more robust checks later
        if os.path.isdir(os.path.realpath(java_home)):
            return java_home
    # Cannot use os.environ.get('JAVA_HOME') because /etc/profile is not sourced by Salt
    # Instead, we'll hope the system has installed Java correctly, in which case
    #   sourcing /etc/profile will tell us the path
    try:
        jh = subprocess.check_output(['/bin/bash', '-c', 'source /etc/profile && echo -n $JAVA_HOME'],
                                     universal_newlines=True)
    except subprocess.CalledProcessError:
        jh = None
    return jh


def _find_keytool(java_home):
    # Find the keytool binary
    for keytool in ['/usr/bin/keytool', java_home + os.sep + 'bin' + os.sep + 'keytool']:
        try:
            subprocess.check_output([keytool] + ['-help'], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            # keytool wasn't found yet
            pass
        else:
            # keytool was found
            return keytool
    # All search options exhausted
    return None
