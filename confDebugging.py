from ligmos.utils import amq, classes, database, confparsers
from ligmos.workers import connSetup


cfile = './alfred.conf'
confclass = classes.hostTarget
pfile = './passwords.conf'

# cfile = './abu.conf'
# confclass = classes.sneakyTarget
# pfile = './passwords.conf'

# Parse the things!
config, comm = confparsers.parseConfig(cfile, confclass,
                                       passfile=pfile,
                                       searchCommon=True,
                                       enableCheck=True,
                                       debug=True)

# Check to see if there are any connections/objects to establish
amqlistener = amq.silentSubscriber()

# NOTE: The idea is that basically ALL of what follows will become completely
#   generic boilerplate, to be shuffled away behind the scenes somewhere
#   for much easier access.  The only thing that might poke out is the stuff
#   above, but even that can be hidden away if we really need/want to do that.

amqtopics = amq.getAllTopics(config, comm)
amqbrokers, influxdatabases = connSetup.establishAMQIDBConnections(comm,
                                                                   amqtopics)

# This part should be in whatever loop gets set up to continually run
#   amqbroker sections containing the connection objects can change, so
#   make sure that we get it back in case a change (reconnection) happened.
amqbrokers = amq.checkConnections(amqbrokers, subscribe=False)
