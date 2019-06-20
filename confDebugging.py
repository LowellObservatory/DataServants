from ligmos.utils import confparsers, classes

cfile = './alfred.conf'
confclass = classes.hostTarget
pfile = './passwords.conf'

# Call the parser DIRECTLY which returns a dict of configparser info in 'conf'
config, comm = confparsers.parseConfig(cfile, confclass,
                                       passfile=pfile,
                                       searchCommon=True,
                                       enableCheck=True,
                                       debug=True)

print(config, comm)
