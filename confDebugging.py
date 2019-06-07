from ligmos.utils import confparsers, confutils, classes


cfile = './alfred.conf'
ctype = classes.hostTarget
pfile = './passwords.conf'

# Call the parser DIRECTLY which returns a dict of configparser info in 'conf'
idict, comm = confparsers.parseConfFile(cfile,
                                        commonBlocks=True,
                                        enableCheck=True,
                                        debug=True)

# Call the helper, which fills a class of type ctype along the way. 'conf2'
#   is then a dict with keys of section names and vals of filled instances
#   of type ctype
idict2, comm2 = confutils.parseConfPasses(cfile, pfile,
                                          conftype=ctype)


print(idict2, comm2)
