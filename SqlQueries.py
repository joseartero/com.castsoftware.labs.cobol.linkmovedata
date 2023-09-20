def drop_temp_tables():
    return "drop table if exists clrbook, clebook, bookmarks"
def populate_clrbook():
    return """
    select acc.idclr, acc.idcle, acc.acctyplo, acc.acctyphi, accbook.* into temporary table clrbook
    from 
    acc,
    keys clr,
    keys cle,
    accbook
    where
        acc.acctyplo & 16777216=16777216
    and acc.acctyphi & 512=512 -- Ar
    and clr.objtyp in (606,548) -- COBOL Paragraph or Section
    and cle.objtyp=831 -- COBOL Data
    and acc.idclr=clr.idkey
    and acc.idcle=cle.idkey    
    and accbook.idacc=acc.idacc
    """
def populate_clebook():
    return """
    select acc.idclr, acc.idcle, acc.acctyplo, acc.acctyphi, accbook.* into temporary table clebook
    from 
    acc,
    keys clr,
    keys cle,
    accbook
    where
        acc.acctyplo & 16777216=16777216
    and acc.acctyphi & 1024=1024 -- Aw
    and clr.objtyp in (606,548) -- COBOL Paragraph or Section
    and cle.objtyp=831 -- COBOL Data
    and acc.idclr=clr.idkey
    and acc.idcle=cle.idkey    
    and accbook.idacc=acc.idacc
    """
def populate_bookmarks():
    return """
    select distinct clrbook.idclr,
                    clrbook.idacc as idacc1, clebook.idacc as idacc2, clrbook.idcle as idcle1, clebook.idcle as idcle2, 
                    clrbook.info1 as info11, clrbook.info2 as info21, clrbook.info3 as info31, clrbook.info4 as info41,
                    clebook.info1 as info12, clebook.info2 as info22, clebook.info3 as info32, clebook.info4 as info42,
                    clrbook.prop as prop1, clrbook.blkno as blkno1,
                    clebook.prop as prop2, clebook.blkno as blkno2,
                    clrbook.acctyphi as acctyphi1, clebook.acctyphi as acctyphi2,
                    keys.keynam as keynam1
    into temporary table bookmarks
    from 
        clrbook,clebook,keys
    where
        clrbook.idclr=clebook.idclr
    and clrbook.idcle=keys.idkey
    and clrbook.info1=clebook.info1
    and clrbook.info2=clebook.info2
    and clrbook.info3=clebook.info3
    and clrbook.info4=clebook.info4
    and clrbook.idcle!=clebook.idcle
    order by 1
    """

def alter_bookmarks():
    return "alter table bookmarks add column bmcode1 text, add column bmcode2 text"

def retrieve_src_bookmarks():
    # Retrieve bookmark src for MOVE statements with ambiguous access type to Cobol Data  (rw,rw or rw,w)
    return """
    update bookmarks set bmcode1 = cust_linkmovedata_extension_code_extractbookmarktext(idacc1,info11,info21,info31,info41,prop1,blkno1),
                         bmcode2 = cust_linkmovedata_extension_code_extractbookmarktext(idacc2,info12,info22,info32,info42,prop2,blkno2)
                     where      (acctyphi1=1536 and acctyphi2=1536) or   -- rw,rw
                                (acctyphi1=1536 and acctyphi2=1024)      -- rw,w
    """

def discard_nomatch1_bookmarks():
    return """
    delete from bookmarks where 
                         bmcode1 is not null and bmcode2 is not null and
                         bmcode1 != bmcode2 -- Bookmark mismatch
    """

def discard_nomatch2_bookmarks():
    return """
    delete from bookmarks where 
                         bmcode1 is not null and bmcode2 is not null
                 and not bmcode1 ~ '[Mm][Oo][Vv][Ee]\s' -- Not a MOVE
    """

def discard_nomatch3_bookmarks():
    return """
    delete from bookmarks where 
                         bmcode1 is not null and bmcode2 is not null                         
                 and not bmcode1 ~ ('[Mm][Oo][Vv][Ee]\s'||replace(keynam1,'-','\-')||'[\s\(]') -- Does not match "MOVE keynam1 ..." => discard
                 and not bmcode1 ~ ('[Mm][Oo][Vv][Ee]\s[Cc][Oo][Rr][Rr][Ee][Ss][Pp][Oo][Nn][Dd][Ii][Nn][Gg]\s'||replace(keynam1,'-','\-')||'[\s\(]')
                 and not bmcode1 ~ ('[Mm][Oo][Vv][Ee]\s[Cc][Oo][Rr][Rr]\s'||replace(keynam1,'-','\-')||'[\s\(]')                         
    """                     

def get_sql_nblinks_created():    
    return "select count(distinct (idcle1, idcle2)) from bookmarks"

def create_cust_linkmovedata_code_extractbookmarktext():
    # Function to retrieve bookmark src
    return """
    CREATE OR REPLACE FUNCTION cust_linkmovedata_extension_code_extractbookmarktext(
        i_idacc integer,
        i_info1 integer,
        i_info2 integer,
        i_info3 integer,
        i_info4 integer,
        i_prop integer,
        i_blkno integer)
        RETURNS text
        LANGUAGE 'plpgsql'
    AS $BODY$
    declare
        L_sourceId int;
        L_source text;
        L_mainStartRow int;
        L_mainStartColumn int;
        L_mainEndRow int;
        L_mainEndColumn int;
        L_startRow int;
        L_startColumn int;
        L_endRow int;
        L_endColumn int;
    begin
        select dcs.SOURCE_ID as sourceId,
                        dcs.SOURCE_CODE as source,
                        op.Info1 as mainStartRow,
                        op.Info2 as mainStartColumn,
                        op.Info3 as mainEndRow,
                        op.Info4 as mainEndColumn,
                        ab.Info1 as startRow,
                        ab.Info2 as startColumn,
                        ab.Info3 as endRow,
                        ab.Info4 as endColumn
                   into L_sourceId,    
                        L_source,
                        L_mainStartRow,
                        L_mainStartColumn,
                        L_mainEndRow,
                        L_mainEndColumn,
                        L_startRow,
                        L_startColumn,
                        L_endRow,
                        L_endColumn
                   from AccBook ab
                   join Acc a
                     on a.IdAcc = ab.IdAcc
                   join ObjPos op
                     on op.IdObj = a.IdClr
                    and (op.BlkNo = 0 or op.BlkNo = ab.BlkNo)
                   join ObjFilRef ofr
                     on (ofr.IdObj = op.IdObj or ofr.IdObj = op.IdObjRef)
                    and (ofr.IdFil = 0 or ofr.IdFil = op.IdObjRef)
                   join RefPath rp
                     on rp.IdFilRef = ofr.IdFilRef
                   join DSS_CODE_SOURCES dcs
                     on dcs.SOURCE_PATH = rp.Path
                  where ab.IdAcc = I_IdAcc
                    and ab.info1=i_info1 and ab.info2=i_info2 and ab.info3=i_info3 and ab.info4=i_info4 
                    and ab.prop=i_prop and ab.blkno=i_blkno;
    
        if L_source is  null
        then
            return null;
        end if;
    
        return CODE_extractBookmarkText(L_sourceId, L_source, L_mainStartRow, L_mainStartColumn, L_mainEndRow, L_mainEndColumn, L_startRow, L_startColumn, L_endRow, L_endColumn);
    
    end;
    $BODY$;
    """