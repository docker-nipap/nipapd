#!/bin/env python2.7

'''This script will generate a base nipapd configuration based on env variables

Will try to default where possible to prevent breakage for values not given.
'''

import os


config_template = '''
# -------------------------
# NIPAP configuration file
# -------------------------


[nipapd]

#user = nipap
#group = nipap


listen = 0.0.0.0
port = 1337

foreground = true
debug = false

fork = 0

# Syslog not configured in most docker containers
syslog = false

pid_file = /var/run/nipapd.pid


db_host = {PGHOST}

db_port = {PGPORT}

db_name = {PGDATABASE}
db_user = {PGUSER}
db_pass = {PGPASS}
db_sslmode = prefer


[auth]
default_backend = local
auth_cache_timeout = 3600

# example backend with SQLite
[auth.backends.local]
type = SqliteAuth

db_path = /etc/nipap/local_auth.db

# example backend for LDAP
#[auth.backends.ldap1]
#type = LdapAuth
#
#basedn = dc=test,dc=com                ; base DN
#uri = ldaps://ldap.test.com            ; LDAP server URI
'''


def write_config(config, path):
    '''Write config to /etc/nipap/nipap.conf if not existent already'''

    if not os.path.exists(path):
        os.makedirs(path)
    file_path = os.path.join(path, 'nipap.conf')
    if not os.path.isfile(file_path):
        with open(os.path.join(file_path), 'w') as config_file:
            config_file.write(config)


def setup_environment():
    '''Setup the local environment'''

    # Set default values if no environment variables found
    default_environment = {
        'PGHOST': 'postgres',
        'PGPORT': '5432',
        'PGDATABASE': 'nipap',
        'PGUSER': 'nipap',
        'PGPASS': 'nipap',
        'NIPAP_USER': '',
        'NIPAP_PASS': '',
        }

    environment = {}
    for var, default in default_environment.iteritems():
        # Prefer user supplied value
        try:
            environment.update({var: os.environ[var]})
        except KeyError:
            if default:
                environment.update({var: default})

    # Set it all back into the environment
    for key, val in environment.iteritems():
        os.environ[key] = val

    return environment


def format_config(environment):
    '''Format the configuration according to provided/default variables'''

    global config_template
    return config_template.format(**environment)


def create_pgpass(environment):
    '''Create .pgpass for psql commands'''

    file_name = os.path.expanduser('~/.pgpass')
    os.environ['PGPASSFILE'] = file_name
    contents = '{PGHOST}:{PGPORT}:{PGDATABASE}:{PGUSER}:{PGPASS}'
    with open(file_name, 'w') as password_file:
        password_file.write('#' + contents + '\n')
        password_file.write(contents.format(**environment))
    os.chmod(file_name, 0600)


def init_db(environment):
    '''Run upstream-provided sql commands to ensure correct db schema'''

    db = environment['PGDATABASE']
    user = environment['PGUSER']
    os.system('psql -d {0} -U {1} -f /sql/ip_net.plsql'.format(db, user))
    os.system('psql -d {0} -U {1} -f /sql/functions.plsql'.format(db, user))
    os.system('psql -d {0} -U {1} -f /sql/triggers.plsql'.format(db, user))


def create_credentials(environment):
    '''Create credentials if environment variables were given for them'''

    try:
        user = environment['NIPAP_USER']
        passwd = environment['NIPAP_PASS']
    except KeyError:
        return
    cmd = 'nipap-passwd -a {0} -p {1} -n "init user"'.format(user, passwd)
    os.system(cmd)



def main():

    # Set up configuration file
    environment = setup_environment()
    config = format_config(environment)
    write_config(config, '/etc/nipap')

    create_pgpass(environment)
    init_db(environment)
    create_credentials(environment)

if __name__ == '__main__':
    main()
