from backend.services.knowledge_updater import KnowledgeUpdater
from backend.core.types.enums import UpdateMode

def main():
    updater = KnowledgeUpdater()
    #updater.run_update(mode=UpdateMode.SINGLE, target_update="storage")
    updater.run_update(mode=UpdateMode.PARTIAL, target_update=["pubsub", "organizations"])

if __name__ == "__main__":
    main()