'''
Created on Sep 11, 2023

@author: GAIC
'''
import cast_upgrade_1_6_13 # @UnusedImport
import logging
import SqlQueries as sqlq
from cast.application import ApplicationLevelExtension

class ApplicationLevelExtension(ApplicationLevelExtension):
    '''
    classdocs
    '''

    def end_application(self, application):
        logging.info('##################################################################')
        kb=application.get_knowledge_base()

        logging.info('Populating temp tables...')
        kb.execute_query(sqlq.drop_temp_tables())
        logging.info('(1/3)')
        kb.execute_query(sqlq.populate_clrbook())
        logging.info('(2/3)')
        kb.execute_query(sqlq.populate_clebook())
        logging.info('(3/3)')
        kb.execute_query(sqlq.populate_bookmarks())
        kb.execute_query(sqlq.alter_bookmarks())
        
        logging.info('Adding function...')
        kb.execute_query(sqlq.create_cust_linkmovedata_code_extractbookmarktext())

        logging.info('Retrieving bookmarks code...')
        kb.execute_query(sqlq.retrieve_src_bookmarks())

        logging.info('Discarding unmatching bookmarks...')
        logging.info('(1/3)')
        kb.execute_query(sqlq.discard_nomatch1_bookmarks())
        logging.info('(2/3)')
        kb.execute_query(sqlq.discard_nomatch2_bookmarks())
        logging.info('(3/3)')
        kb.execute_query(sqlq.discard_nomatch3_bookmarks())
        
        logging.info('Creating links...')
        # Creates Aw link between source->target Cobol Data items in MOVE statements
        application.update_cast_knowledge_base("Create links between Cobol Data items", """        
        insert into CI_LINKS (CALLER_ID, CALLED_ID, LINK_TYPE, ERROR_ID)        
            select distinct idcle1, idcle2, 'accessWriteLink', 0
            from bookmarks
        """)
        nblinks_rs=kb.execute_query(sqlq.get_sql_nblinks_created())
        for row in nblinks_rs:
            nblinks=row[0]
        logging.info('*********************************')
        logging.info('Number of links created: '+str(nblinks))
        logging.info('*********************************')
        logging.info('Cleanup...')
        kb.execute_query(sqlq.drop_temp_tables())
        logging.info('##################################################################')
