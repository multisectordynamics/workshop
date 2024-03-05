import io
import os
import pkg_resources

import duckdb
import numpy as np
import pandas as pd
import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt


sns.set_theme(style="whitegrid")


# default values
MAX_REVIEWS_PER_DOCUMENT = 3
MAX_REVIEWS_PER_REVIEWER = 15


def create_db_connection():
    dat_file = os.path.join(os.getcwd(), "data", "data.duckdb")
    return duckdb.connect(dat_file)


def reset_session(coi_reset=True):
    """
    This function resets the session state variables to their default values.
    It is used to prepare the environment for a new review session.
    """
    # Set the completion status of the review to False
    st.session_state.complete = False
    # Set the acceptance status of the review to False
    st.session_state.accept = False
    # Set the required number of reviews to the maximum reviews per reviewer
    st.session_state.required_reviews = st.session_state.max_reviews_per_reviewer
    # Initialize the conflict of interest status to "Select Option"
    st.session_state.conflict = "Select Option"
    # Initialize the career level score to an empty string
    st.session_state.career = ""
    # Initialize the workshop alignment score to an empty string
    st.session_state.alignment = ""
    # Initialize the advancing MSD science score to an empty string
    st.session_state.science = ""
    # Initialize the benefits score to an empty string
    st.session_state.benefits = ""
    # Initialize the comments to an empty string
    st.session_state.comments = ""

    st.session_state.comments_submit_button = False

    st.session_state.active = False

    if coi_reset:
        st.session_state.coi_complete = False


def clear_criteria():

    if st.session_state.redo:
        sql = f"""
        UPDATE
            tbl_response
        SET 
            alignment = {st.session_state.alignment}
            ,science = {st.session_state.science}
            ,benefits = {st.session_state.benefits}
            ,comments = '{st.session_state.comments}'
        WHERE 
            document_id = {st.session_state.document_id}
            AND reviewer_id = {st.session_state.reviewer_id}
        """

    else:

        sql = f"""
        INSERT INTO tbl_response(
            reviewer_id 
            ,reviewer_name
            ,document_id
            --,career
            ,alignment
            ,science
            ,benefits
            ,comments
            ,screening_order
        ) 
        VALUES (
            {st.session_state.reviewer_id}, 
            '{st.session_state.reviewer_name}',
            {st.session_state.document_id}, 
            --{st.session_state.career},
            {st.session_state.alignment},
            {st.session_state.science},
            {st.session_state.benefits},
            '{st.session_state.comments}',
            {st.session_state.screening_order}
        );
        """

    st.session_state.cursor.sql(sql)
    st.session_state.cursor.commit()

    st.session_state.accept = False

    st.session_state.conflict = "Select Option"
    st.session_state.career = ""
    st.session_state.alignment = ""
    st.session_state.science = ""
    st.session_state.benefits = ""
    st.session_state.comments = ""
    st.session_state.comments_submit_button = False
    st.session_state.screening_order += 1

    js = '''
    <script>
        var body = window.parent.document.querySelector(".main");
        //console.log(body);
        body.scrollTop = 0;
    </script>
    '''

    st.components.v1.html(js)

    st.components.v1.html(js)

    # set back to false if record edit in progress
    st.session_state.redo = False

    # set active review to false
    st.session_state.active = False


def plot_progress_data():

    sql = f"""
    SELECT 
        reviewer_name
        ,ROUND((COUNT(reviewer_name) - 1 )/  {st.session_state.max_reviews_per_reviewer}, 2) as fraction_complete
        ,1 as total
    FROM (
        SELECT reviewer_name FROM tbl_reviewer
        UNION ALL
        SELECT reviewer_name FROM tbl_response
    )
    GROUP BY 
        reviewer_name
    ORDER BY
        ROUND((COUNT(reviewer_name) - 1 )/  {st.session_state.max_reviews_per_reviewer}, 2)
    DESC
    """

    df = st.session_state.cursor.sql(sql).df()

    fig, ax = plt.subplots(figsize=(6, 10))

    # plot the total fraction 
    sns.set_color_codes("pastel")
    sns.barplot(x="total", 
                y="reviewer_name", 
                data=df,
                label="Total", 
                color="b")

    # Plot the crashes where alcohol was involved
    sns.set_color_codes("muted")
    sns.barplot(x="fraction_complete", 
                y="reviewer_name", 
                data=df,
                label="Fraction Completed", 
                color="b")

    # Add a legend and informative axis label
    ax.set(xlim=(0, 1), 
        ylabel="",
        xlabel="Fraction Completed",
        title="Fraction of Review Documents Completed")
    sns.despine(left=True, bottom=True)

    return fig


def generate_selection():

    sql = f"""
    SELECT
        CONCAT(first_name, ' ', last_name) as authors
        ,institution as affiliation
        ,authors as coauthors
        ,title
        ,abstract
        ,biosketch
        ,leverage_plan
        ,early_career
        ,student
        ,document_id 
    FROM 
        tbl_source 
    -- ensure we do not draw any records for which a conflict of interest was stated
    WHERE document_id NOT IN (
        SELECT document_id FROM tbl_log WHERE reviewer_id = {st.session_state.reviewer_id} AND conflict = 'YES'
    )
    -- no draws from records already inventoried by the reviewer
    AND document_id NOT IN (
        SELECT document_id FROM tbl_response WHERE reviewer_id = {st.session_state.reviewer_id}
    )
    -- no draws from records already having the maximum number of reviews
    AND document_id NOT IN (
        SELECT document_id
        FROM tbl_response
        GROUP BY document_id
        HAVING COUNT(document_id) >= {st.session_state.max_reviews_per_document}
    )
    -- no draws after the number of required reviews has been met
    AND (
        SELECT COUNT(reviewer_id) FROM tbl_response WHERE reviewer_id = {st.session_state.reviewer_id}
    ) < {st.session_state.required_reviews}
    ORDER BY 
        RANDOM() LIMIT 1;
    """

    return st.session_state.cursor.sql(sql).df()


def coi_review_selection():

    sql = f"""
    SELECT 
        document_id
        ,CONCAT(first_name, ' ', last_name) as author
        ,institution as affiliation
        ,CASE WHEN authors IS NULL THEN 'NA' ELSE authors  END as coauthors
    FROM tbl_source
    WHERE document_id NOT IN (
        SELECT document_id FROM tbl_log WHERE reviewer_id = {st.session_state.reviewer_id} 
    )
    ORDER BY RANDOM() LIMIT 1;
    """

    selection = st.session_state.cursor.sql(sql).df()

    if selection.shape[0] == 0:
        st.session_state.complete = False
        st.session_state.coi_complete = True
        reset_session(coi_reset=False)
    else:

        try:
            st.session_state.authors = selection["author"].values[0].replace(";", ",").replace("\n", ". ")
            st.session_state.affiliation = selection["affiliation"].values[0].replace(";", ",").replace("\n", ". ")
            st.session_state.coauthors = selection["coauthors"].values[0].replace(";", ",").replace("\n", ". ")
            st.session_state.document_id = selection["document_id"].values[0]
        except:
            st.write(selection)
            raise

    return selection


def coi():

    # update database
    sql = f"""
    INSERT INTO tbl_log (reviewer_id, document_id, conflict) 
    VALUES ({st.session_state.reviewer_id}, {st.session_state.document_id}, '{st.session_state.conflict}');
    """
    st.session_state.cursor.sql(sql)
    st.session_state.cursor.commit()

    # regenerate selection
    st.session_state.conflict = "Select Option"


def clearance():

    if st.session_state.userpw == os.getenv("APP1"):
        st.session_state.permit = True 

    elif st.session_state.permit is False and st.session_state.userpw != "":
        st.warning("Incorrect password.  Try again.")


def clean_slate():

    st.session_state.cursor.sql("truncate tbl_response;")
    st.session_state.cursor.sql("truncate tbl_log;")
    st.session_state.cursor.commit()
    st.success("Database has been reset.")


def get_nrecords():
    return st.session_state.cursor.sql("SELECT COUNT(1) as ct FROM tbl_source").df()["ct"].values[0]


def get_coi_count():

    sql = f"SELECT COUNT(1) as ct FROM tbl_log WHERE reviewer_id = {st.session_state.reviewer_id}"
    return st.session_state.cursor.sql(sql).df()["ct"].values[0]


def get_record_count():

    sql = f"SELECT COUNT(1) as ct FROM tbl_response WHERE reviewer_id = {st.session_state.reviewer_id}"
    return st.session_state.cursor.sql(sql).df()["ct"].values[0]


def clear_text():
    st.session_state.comments_persist = st.session_state.comments
    st.session_state.comments = ""


def refresh_user():
    st.session_state.complete = False

    sql = f"DELETE FROM tbl_response WHERE reviewer_id = {st.session_state.reviewer_id};"

    st.session_state.cursor.sql(sql)
    st.session_state.cursor.commit()


def get_previous_order():

    sql = f"""
    SELECT 
        MAX(screening_order) as mx 
    FROM 
        tbl_response
    WHERE 
        reviewer_id = {st.session_state.reviewer_id}
    """

    return st.session_state.cursor.sql(sql).df()["mx"].values[0]


def redo_previous_record():

    st.session_state.complete = False

    # get the previous records screening order number
    order = get_previous_order()

    sql = f"""
    SELECT 
        a.document_id
        ,a.alignment
        ,a.science
        ,a.benefits
        ,a.comments
        ,a.screening_order
        ,b.title
        ,b.abstract
        ,b.biosketch
        ,b.leverage_plan
        ,b.student
        ,b.early_career
    FROM
        tbl_response a
    INNER JOIN
        tbl_source b
    ON
        a.document_id = b.document_id
    WHERE
        a.reviewer_id = {st.session_state.reviewer_id}
        AND a.screening_order = {order}
    """

    response = st.session_state.cursor.sql(sql).df()

    st.session_state.document_id = response["document_id"].values[0]
    st.session_state.alignment = response["alignment"].values[0]
    st.session_state.science = response["science"].values[0]
    st.session_state.benefits = response["benefits"].values[0]
    st.session_state.comments = response["comments"].values[0]
    st.session_state.title = response["title"].values[0].replace(";", ",").replace("\n", ". ")
    st.session_state.abstract = response["abstract"].values[0].replace(";", ",").replace("\n", ". ")
    st.session_state.biosketch = response["biosketch"].values[0].replace(";", ",").replace("\n", ". ")
    st.session_state.leverage_plan = response["leverage_plan"].values[0].replace(";", ",").replace("\n", ". ")
    st.session_state.early_career = response["early_career"].values[0].replace(";", ",").replace("\n", ". ")
    st.session_state.student = response["student"].values[0].replace(";", ",").replace("\n", ". ")
    st.session_state.screening_order = order

    st.session_state.comments_redo = st.session_state.comments

    # set to record redo
    st.session_state.redo = True


# set persistent session state variables
if "session" not in st.session_state:
    conn = create_db_connection()
    st.session_state.cursor = conn.cursor()

if "reviewer_dict" not in st.session_state:
    sql = "SELECT reviewer_name, reviewer_id FROM tbl_reviewer;"
    d = st.session_state.cursor.sql(sql).df().set_index("reviewer_name")["reviewer_id"].to_dict()
    st.session_state.reviewer_dict = d

if "reviwer_name_tuple" not in st.session_state:
    sql = "SELECT DISTINCT(reviewer_name) as nm FROM tbl_reviewer ORDER BY reviewer_name;"
    name_tuple = tuple(st.session_state.cursor.sql(sql).df()["nm"].to_list())
    st.session_state.reviwer_name_tuple = name_tuple

if "reviewer_id" not in st.session_state:
    st.session_state.reviewer_id = None

if "reviewer_name" not in st.session_state:
    st.session_state.reviewer_name = None

if "required_reviews" not in st.session_state:
    st.session_state.required_reviews = 1 #st.session_state.max_reviews_per_reviewer 

if "authors" not in st.session_state:
    st.session_state.authors = None

if "affiliation" not in st.session_state:
    st.session_state.affiliation = None

if "title" not in st.session_state:
    st.session_state.title = None

if "abstract" not in st.session_state:
    st.session_state.abstract = None

if "document_id" not in st.session_state:
    st.session_state.document_id = None

if "selection" not in st.session_state:
    st.session_state.selection = None

if "accept" not in st.session_state:
    st.session_state.accept = False

if "complete" not in st.session_state:
    st.session_state.complete = False

if "career" not in st.session_state:
    st.session_state.career = ""

if "alignment" not in st.session_state:
    st.session_state.alignment = ""

if "science" not in st.session_state:
    st.session_state.science = ""

if "benefits" not in st.session_state:
    st.session_state.benefits = ""

if "comments" not in st.session_state:
    st.session_state.comments = ""

if "query" not in st.session_state:
    st.session_state.query = None

if "mode" not in st.session_state:
    st.session_state.mode = "Reviewer"

if "show_progress" not in st.session_state:
    st.session_state.show_progress = False

if "userpw" not in st.session_state:
    st.session_state.userpw = ""

if "permit" not in st.session_state:
    st.session_state.permit = False

if "coi_complete" not in st.session_state:
    st.session_state.coi_complete = False

if "coauthors" not in st.session_state:
    st.session_state.coauthors = ""

if "name_selected" not in st.session_state:
    st.session_state.name_selected = False

if "coi_nrecords" not in st.session_state:
    st.session_state.coi_nrecords = get_nrecords()

if "coi_count" not in st.session_state:
    st.session_state.coi_count = 0

if "review_count" not in st.session_state:
    st.session_state.review_count = 0

if "comments_submit_button" not in st.session_state:
    st.session_state.comments_submit_button = False

if "screening_order" not in st.session_state:
    st.session_state.screening_order = 0

if "redo" not in st.session_state:
    st.session_state.redo = False

if "active" not in st.session_state:
    st.session_state.active = False

if "max_reviews_per_document" not in st.session_state:
    st.session_state.max_reviews_per_document = MAX_REVIEWS_PER_DOCUMENT

if "max_reviews_per_reviewer" not in st.session_state:
    st.session_state.max_reviews_per_reviewer = MAX_REVIEWS_PER_REVIEWER



# start with sidebar open
with st.sidebar:

    st.markdown("### Settings")

    st.selectbox(
        '**Select mode**:',
        ("Reviewer", "Admin"),
        index=0,
        key="mode"
    )

    # st.number_input(
    #     '**Set the maximum number of reviews allowable per document**:',
    #     min_value=1,
    #     max_value=1000,
    #     value=MAX_REVIEWS_PER_DOCUMENT,
    #     step=1,
    #     key="max_reviews_per_document"
    # )

    # st.number_input(
    #     '**Set the maximum number of reviews allowable per reviewer**:',
    #     min_value=1,
    #     max_value=1000,
    #     value=MAX_REVIEWS_PER_REVIEWER,
    #     step=1,
    #     key="max_reviews_per_reviewer"
    # )

    st.session_state.required_reviews = st.session_state.max_reviews_per_reviewer

# if reviewer panel is chosen
if st.session_state.mode == "Reviewer":

    # if credential have not yet been accepted
    if st.session_state.permit is False:

        st.text_input(
            label="**Enter your password**",
            placeholder="*******",
            type="password",
            key="userpw",
            on_change=clearance
        )

    # if credentials are accepted
    elif st.session_state.permit: 

        st.header("MSD CoP Workshop Abstract Screening", anchor="top")

        reviewer_block = st.container()

        st.session_state.reviewer_name = reviewer_block.selectbox(
                '##### Select your name:',
                (None,) + st.session_state.reviwer_name_tuple,
                index=0,
                on_change=reset_session
        )

        if st.session_state.reviewer_name is not None:

            reviewer_block.markdown(f"##### Session active for:  {st.session_state.reviewer_name}")

            # get the reviewer id from the reviewer name
            st.session_state.reviewer_id = st.session_state.reviewer_dict[st.session_state.reviewer_name]

            # get the count of how many conflict of interest (coi) records have been evaluated for the reviwer
            st.session_state.coi_count = get_coi_count()

            # if the reviewer has completed all COI reviews mark as complete
            if st.session_state.coi_count == st.session_state.coi_nrecords:
                st.session_state.coi_complete = True

            # step 1.  conduct full COI evaluation before reviews are allowed
            if st.session_state.coi_complete is False:
                coi_block = st.container()
                coi_block.header("Conflict of Interest Screening") 
                coi_block.markdown("You must complete the conflict of interest screening before continuing the review.")

                # get the current count of COI records that have been reviewed
                st.session_state.coi_count = get_coi_count()

                coi_block.warning(f"Conflict of Interest (COI) screening progress:  {st.session_state.coi_count} of {st.session_state.coi_nrecords}")

                # generate a COI record new selection
                st.session_state.selection = coi_review_selection()

                if st.session_state.coi_complete is False:

                    # ask for conflict of interest?  if yes regenerate selection excluding COI
                    coi_block.markdown(f"##### Do you have a conflict of interest with the following author(s)?:") 

                    coi_block.markdown(
                        f"""
                        - **Lead Author**:  {st.session_state.authors}
                        - **Affiliation**:  {st.session_state.affiliation}
                        - **Coauthors**:  {st.session_state.coauthors}
                        """
                    )

                    coi_block.selectbox(
                        '**Select YES or NO**:',
                        ("Select Option", "NO", "YES"),
                        index=0,
                        key="conflict",
                        on_change=coi
                    )

            else:

                reviewer_block.success("Conflict of Interest (COI) screening complete!")

                reviewer_block.header(f"Submission Screening") 

                # update the record count with the current number that the reviewer has reviewed
                st.session_state.review_count = get_record_count()

                reviewer_block.warning(f"Review progress:  completed {st.session_state.review_count} of {st.session_state.max_reviews_per_reviewer}")

                # offer option to redo the last record
                if st.session_state.review_count > 0:
                    reviewer_block.markdown("##### Want to redo the previous record?")
                    reviewer_block.button(":boom: Redo the Previous Record :boom:",  on_click=redo_previous_record) 

                reviewer_block.markdown(f"##### Selected Review:") 

                # if the review is not complete and not in a redo
                if st.session_state.complete is False and st.session_state.redo is False and st.session_state.active is False:

                    # populate selection criteria
                    st.session_state.selection = generate_selection()

                    # if the selection comes back empty then set review completion status to True
                    if st.session_state.selection.shape[0] == 0:
                        st.session_state.complete = True
                    else:
                        st.session_state.authors = st.session_state.selection["authors"].values[0].replace(";", ",").replace("\n", ". ")
                        st.session_state.affiliation = st.session_state.selection["affiliation"].values[0].replace(";", ",").replace("\n", ". ")
                        st.session_state.coauthors = str(st.session_state.selection["coauthors"].values[0])
                        if st.session_state.coauthors is None:
                            st.session_state.coauthors = ""
                        else:
                            st.session_state.coauthors = st.session_state.coauthors.replace(";", ",").replace("\n", ". ")
                        st.session_state.title = st.session_state.selection["title"].values[0].replace(";", ",").replace("\n", ". ")
                        st.session_state.abstract = st.session_state.selection["abstract"].values[0].replace(";", ",").replace("\n", ". ")
                        st.session_state.document_id = st.session_state.selection["document_id"].values[0]
                        st.session_state.biosketch = st.session_state.selection["biosketch"].values[0].replace(";", ",").replace("\n", ". ")
                        st.session_state.early_career = st.session_state.selection["early_career"].values[0].replace(";", ",").replace("\n", ". ")
                        st.session_state.leverage_plan = st.session_state.selection["leverage_plan"].values[0].replace(";", ",").replace("\n", ". ")
                        st.session_state.student = st.session_state.selection["student"].values[0].replace(";", ",").replace("\n", ". ")

                if st.session_state.complete is False:  

                    reviewer_block.markdown(
                        f"""
                        - **Title**:  {st.session_state.title}
                        - **Abstract**:  {st.session_state.abstract}
                        - **Biosketch**:  {st.session_state.biosketch}
                        - **Leverage Plan**:  {st.session_state.leverage_plan}
                        - **Early Career**:  {st.session_state.early_career}
                        - **Student**:  {st.session_state.student}
                        """
                    )

                    st.session_state.active = True

                elif st.session_state.complete:
                    reviewer_block.success("Thank you!  You have either hit your max or there are no documents left to review.")

                    # reviewer_block.markdown(
                    #     """
                    #     <iframe width="560" height="315" src="https://www.youtube.com/embed/3GwjfUFyY6M?autoplay=1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
                    #     """,
                    #     unsafe_allow_html=True,
                    # )

                    reviewer_block.markdown("##### Want to start over and do the screening again from scratch?")
                    reviewer_block.button(":boom: Erase and Start Over :boom:",  on_click=refresh_user) 


                if st.session_state.complete is False:  

                    # add a streamlit checkbox for the review checklist criteria
                    criteria_block = st.container()
                    criteria_block.markdown("#### Applicant Review")
                    criteria_block.markdown("Fill out the review criteria for each metric below")

                    # criteria_block.markdown("##### Early Career and/or Student")
                    # criteria_block.markdown(
                    #     """
                    #     **Scoring**:
                    #     1. Not early career or student
                    #     2. Early career or student
                    #     """
                    # )

                    # criteria_block.selectbox(
                    #     '**Select score from 1 or 2**:',
                    #     ("", 1, 2),
                    #     index=0,
                    #     key="career"
                    # )

                    criteria_block.markdown("##### Alignment with workshop goals")
                    criteria_block.markdown(
                        """
                        **Description**:
                        - Dissemination of existing MSD models, data, and methods
                        - Interdisciplinary collaboration
                        - Working Group integration
                        - Developing SF manuscripts

                        **Scoring**:
                        1. Potential to contribute unclear
                        2. Potential to contribute to one or more goals
                        3. Clear potential/history to contribute to more than one goal
                        4. Concrete and feasible plans for (or history of) contribution to more than one goal
                        """
                    )

                    criteria_block.selectbox(
                        '**Select score from 1 to 4**:',
                        ("", 1, 2, 3, 4),
                        index=0,
                        key="alignment"
                    )

                    criteria_block.markdown("##### Advancing MSD science")
                    criteria_block.markdown(
                        """
                        **Scoring**:
                        1. Irrelevant or of insufficient quality
                        2. MSD-relevant research of sufficient quality or impact
                        3. MSD-relevant research that appears high quality (innovative and high impact)
                        4. Research of high innovation, quality, and impact that advances key questions in MSD 1 non-MSD relevant, or not high quality or not high impact
                        """
                    )

                    criteria_block.selectbox(
                        '**Select score from 1 to 4**:',
                        ("", 1, 2, 3, 4),
                        index=0,
                        key="science"
                    )

                    criteria_block.markdown("##### Benefits to attendee")
                    criteria_block.markdown(
                        """
                        **Scoring**:
                        1. Does not articulate plans to leverage workshop
                        2. Articulates potential benefits that may be less relevant to career or less significant
                        3. Clearly articulates potential benefits for career development
                        4. Clearly articulates significant benefits of attending the workshop for career development
                        """
                    )

                    criteria_block.selectbox(
                        '**Select score from 1 to 4**:',
                        ("", 1, 2, 3, 4),
                        index=0,
                        key="benefits"
                    )

                    criteria_block.markdown("##### Area of expertise / Optional comments")
                    
                    with criteria_block.form(key="comment_form", clear_on_submit=True):
                        st.session_state.comments = st.text_input("**What do you believe the area of expertise is for the applicant?**")
                        st.session_state.comments_submit_button = st.form_submit_button("Commit Entry")

                    if st.session_state.comments_submit_button and st.session_state.redo is False:
                        criteria_block.info(f"**Your entry**: {st.session_state.comments}")

                    elif st.session_state.comments_submit_button and st.session_state.redo:
                            criteria_block.info(f"**Your entry**: {st.session_state.comments}")

                    elif st.session_state.comments_submit_button is False and st.session_state.redo:
                        st.session_state.comments = st.session_state.comments_redo
                        criteria_block.info(f"**Your entry**: {st.session_state.comments}")
                    
                    else:
                        st.session_state.comments = ""


                    if  st.session_state.alignment == "" or st.session_state.science == "" or st.session_state.benefits  == "" or st.session_state.comments == "":

                        # if st.session_state.career == "":
                        #     st.warning("Please enter a valid score for 'Early Career and/or Student' to continue.")

                        if st.session_state.alignment == "":
                            st.warning("Please enter a valid score for 'Alignment with workshop goals' to continue.")

                        if st.session_state.science == "":
                            st.warning("Please enter a valid score for 'Advancing MSD science' to continue.")

                        if st.session_state.benefits == "":
                            st.warning("Please enter a valid score for 'Benefits to attendee' to continue.")

                        if st.session_state.comments == "":
                            st.warning("Please enter text for 'Area of expertise' to contintue.")

                    else:
                
                        advance = st.container()
                        advance.markdown("##### Click to commit changes and move to the next document in your review queue")
                        next_button = st.button("Next Document",  on_click=clear_criteria)  

                reviewer_response_block = st.container()

                st.session_state.show_progress = reviewer_response_block.checkbox("Show progress", value=True)
                

                if st.session_state.show_progress:
                    reviewer_response_sql = f"""
                        SELECT 
                            --a.reviewer_id
                            a.reviewer_name
                            --,a.document_id
                            ,b.title
                            --,CONCAT(b.first_name, ' ', b.last_name) as author
                            --,b.institution as affiliation
                            --,b.authors as coauthors
                            ,b.abstract
                            ,b.biosketch
                            ,b.leverage_plan
                            ,b.student
                            ,b.early_career
                            --,b.registration_waiver
                            --,b.travel_award
                            --,b.poster_competition
                            --,b.breakout_sessions
                            --,a.career AS career_level
                            ,a.alignment AS workshop_alignment
                            ,a.science AS advancing_msd_science
                            ,a.benefits
                            ,a.comments
                        FROM 
                            tbl_response as a
                        INNER JOIN
                            tbl_source as b 
                        ON
                            a.document_id = b.document_id
                        WHERE
                            a.reviewer_id = {st.session_state.reviewer_id}
                        ORDER BY
                            a.screening_order
                        """
                    reviewer_result_df = st.session_state.cursor.sql(reviewer_response_sql).df()
                    
                    reviewer_response_block.markdown("##### Reviewer progress:")

                    reviewer_response_block.write(reviewer_result_df)


                    if reviewer_result_df is not None:
                        reviewer_response_block.markdown("###### Export reviewer responses to CSV file:")
                        bio = io.BytesIO()
                        reviewer_result_df.to_csv(bio, index=False)
                        reviewer_response_block.download_button(
                            label="Export to CSV",
                            data=bio.getvalue(),
                            file_name=f"""{st.session_state.reviewer_name.replace(" ", "_").lower()}_reviewer_responses.csv""",
                            mime="csv"
                        )      

elif st.session_state.mode == "Admin":
    st.markdown("#### Admininstrative Only")

    admin_block = st.container()

    pw = admin_block.text_input(
            label="**Enter your password**",
            placeholder="*******",
            type="password")

    if pw == os.getenv("APP0"):
        admin_block.markdown("##### All reviewer responses:")
        response_sql = """
        SELECT 
            a.reviewer_id
            ,a.reviewer_name
            ,a.document_id
            ,b.institution as affiliation
            ,b.authors as coauthors
            ,b.abstract
            --,a.career AS career_level
            ,a.alignment AS workshop_alignment
            ,a.science AS advancing_msd_science
            ,a.benefits
            ,a.comments
        FROM 
            tbl_response as a
        INNER JOIN
            tbl_source as b 
        ON
            a.document_id = b.document_id
        """
        summary_result_df = st.session_state.cursor.sql(response_sql).df()
        admin_block.write(summary_result_df)

        if summary_result_df is not None:
            admin_block.markdown("###### Export reviewer responses to CSV file:")
            bio = io.BytesIO()
            summary_result_df.to_csv(bio, index=False)
            admin_block.download_button(
                label="Export to CSV",
                data=bio.getvalue(),
                file_name="reviewer_responses.csv",
                mime="csv"
            )

        admin_block.markdown("##### Current review progress:")
        progress_fig = plot_progress_data()
        admin_block.pyplot(progress_fig)

        admin_block.markdown("##### Query database for additional insights")
        st.session_state.query = admin_block.text_area(
            label="**Please enter your SQL query here.**",
            height=100
        )

        if st.session_state.query:
            try:
                query_result_df = st.session_state.cursor.sql(st.session_state.query).df()

                admin_block.markdown("##### Query Result")
            except Exception as e:
                admin_block.error(f"Error: {e}")
                query_result_df = None
    
            if query_result_df is not None:
                admin_block.write(query_result_df)

                admin_block.markdown("###### Export query results to a CSV file:")
                bio = io.BytesIO()
                query_result_df.to_csv(bio, index=False)
                admin_block.download_button(
                    label="Export to CSV",
                    data=bio.getvalue(),
                    file_name="query_response.csv",
                    mime="csv"
                )
