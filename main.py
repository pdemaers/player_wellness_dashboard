from streamlit_option_menu import option_menu
from streamlit_authenticator import Authenticate
import streamlit as st
from db.mongo_wrapper import MongoWrapper, DatabaseError
from views import roster_management, session_management, wellness_dashboard, rpe_dashboard, session_dashboard, pdp_structure_management, player_pdp, pdp_library

# Constants
TEAMS = ["U18", "U21"]

# --- ROLE CONFIG --------------------------------------------------------------
PAGES = {
    "Roster Management": lambda mongo, user: roster_management.render(mongo, user=user),
    "Session Management": lambda mongo, user: session_management.render(mongo, user=user),
    "PDP Structure":     lambda mongo, user: pdp_structure_management.render(mongo, user=user),
    "Wellness Dashboard":lambda mongo, user: wellness_dashboard.render(mongo, user=user),
    "RPE Dashboard":     lambda mongo, user: rpe_dashboard.render(mongo, user=user),
    "Session Dashboard": lambda mongo, user: session_dashboard.render(mongo, user=user),
    "Create PDP":        lambda mongo, user: player_pdp.render(mongo, user=user),
    "PDP Library":       lambda mongo, user: pdp_library.render(mongo, user=user),
}

PAGE_ICONS = {
    "Roster Management": "people-fill",
    "Session Management": "calendar2-event-fill",
    "PDP Structure": "file-earmark-text",
    "Wellness Dashboard": "heart-pulse",
    "RPE Dashboard": "bar-chart-line",
    "Session Dashboard": "clipboard-data",
    "Create PDP": "file-earmark-plus",
    "PDP Library": "archive",
}

ROLE_ALLOWED_PAGES = {
    "admin": list(PAGES.keys()),
    "coach": [
        "Wellness Dashboard", "RPE Dashboard", "Session Dashboard",
        "Create PDP", "PDP Library"
    ],
    "physio": [
        "Wellness Dashboard", "RPE Dashboard"
    ],
}

def get_user_role(username: str) -> str:
    """
    Get role for the authenticated user from secrets.
    Supports two layouts:
      1) st.secrets['authentication']['credentials']['usernames'][<u>]['role']
      2) st.secrets['authentication']['roles'][<u>]
    Defaults to 'coach' if missing.
    """
    try:
        return st.secrets["authentication"]["credentials"]["usernames"][username].get("role", "coach")
    except Exception:
        try:
            return st.secrets["authentication"]["roles"].get(username, "coach")
        except Exception:
            return "coach"

def allowed_pages_for(role: str) -> list[str]:
    return ROLE_ALLOWED_PAGES.get(role, ROLE_ALLOWED_PAGES["coach"])

def guard_access(role: str, page: str) -> None:
    if page not in allowed_pages_for(role):
        st.error("You do not have access to this page.")
        st.stop()

# --- YOUR MAIN() WITH MINIMAL CHANGES ----------------------------------------

def main():
    """Main application entry point."""
    # Configure page
    st.set_page_config(
        page_title="Player Management System",
        page_icon="⚽",
        layout="wide"
    )
    
    # --- AUTHENTICATION ---
    authenticator = Authenticate(
        credentials=st.secrets['authentication']['credentials'].to_dict(),
        cookie_name=st.secrets['authentication']['cookie']['name'],
        key=st.secrets['authentication']['cookie']['key'],
        cookie_expiry_days=st.secrets['authentication']['cookie']['expiry_days'],
        preauthorized=st.secrets['authentication']['preauthorized']['emails']
    )

    try:
        authenticator.login()
    except Exception as e:
        st.error(f"Authentication error: {e}")
        st.stop()

    auth_status = st.session_state.get("authentication_status")

    if auth_status:
        authenticator.logout("Logout", "sidebar")

        # Read username set by streamlit-authenticator
        username = st.session_state.get("username")
        role = get_user_role(username or "")
        st.session_state["role"] = role  # handy elsewhere

        with st.sidebar:
            st.write(f':material/waving_hand: Welcome *{st.session_state.get("name")}*')
            st.caption(f"Role: `{role}`")

            # Init Mongo wrapper
            mongo = MongoWrapper(st.secrets["MongoDB"])

            # --- SIDEBAR MENU (role-aware) ---
            role_options = allowed_pages_for(role)
            selected = option_menu(
                menu_title="Main Menu",
                options=role_options,  # only show allowed pages
                icons=[PAGE_ICONS[p] for p in role_options],  # match lengths
                default_index=0
            )

        # --- ROUTING (with guard) ---
        guard_access(role, selected)
        PAGES[selected](mongo, user=username)



        # --- ROUTING ---
        # if selected == "Roster Management":
        #     roster_management.render(mongo, user=st.session_state["username"])  # Modular function
        # elif selected == "Session Management":
        #     session_management.render(mongo, user=st.session_state["username"])
        # elif selected == "PDP Structure":
        #     pdp_structure_management.render(mongo, user=st.session_state["username"])
        # elif selected == "Wellness Dashboard":
        #     wellness_dashboard.render(mongo, user=st.session_state["username"])
        # elif selected == "RPE Dashboard":
        #     rpe_dashboard.render(mongo, user=st.session_state["username"])
        # elif selected == "Session Dashboard":
        #     session_dashboard.render(mongo, user=st.session_state["username"])
        # elif selected == "Create PDP":
        #     player_pdp.render(mongo, user=st.session_state["username"])
        # elif selected == "PDP Library":
        #     pdp_library.render(mongo, user=st.session_state["username"])

    elif auth_status is False:
        st.error(":material/error: Username or password is incorrect")
    else:
        st.warning("Please enter your username and password")

# Run app
if __name__ == "__main__":
    main()