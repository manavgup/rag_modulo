from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from rag_solution.file_management.database import get_db
from rag_solution.schemas.team_schema import TeamInput, TeamOutput
from rag_solution.schemas.user_team_schema import UserTeamInput, UserTeamOutput
from rag_solution.services.team_service import TeamService
from rag_solution.services.user_team_service import UserTeamService

router = APIRouter(prefix="/api/teams", tags=["teams"])


def get_team_service(db: Session = Depends(get_db)) -> TeamService:
    """
    Get an instance of the TeamService.

    Args:
        db (Session): The database session.

    Returns:
        TeamService: An instance of the TeamService.
    """
    return TeamService(db)


def get_user_team_service(db: Session = Depends(get_db)) -> UserTeamService:
    """
    Get an instance of the UserTeamService.

    Args:
        db (Session): The database session.

    Returns:
        UserTeamService: An instance of the UserTeamService.
    """
    return UserTeamService(db)


@router.post(
    "",
    response_model=TeamOutput,
    summary="Create a new team",
    description="Create a new team with the provided input data",
    responses={
        201: {"description": "Team created successfully"},
        400: {"description": "Invalid input data"},
        500: {"description": "Internal server error"},
    },
)
def create_team(team: TeamInput, db: Session = Depends(get_db)) -> TeamOutput:
    """
    Create a new team.

    Args:
        team (TeamInput): The input data for creating a team.
        db (Session): The database session.

    Returns:
        TeamOutput: The created team.

    Raises:
        HTTPException: If there's an error creating the team.
    """
    team_service = get_team_service(db)
    try:
        return team_service.create_team(team)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/{team_id}/users/{user_id}/role",
    response_model=UserTeamOutput,
    summary="Update a user's role in a team",
    description="Update the role of a user within a specific team",
    responses={
        200: {"description": "User role updated successfully"},
        404: {"description": "Team association not found"},
        500: {"description": "Internal server error"},
    },
)
def update_user_role_in_team(team_id: UUID, user_id: UUID, role: str, db: Session = Depends(get_db)) -> UserTeamOutput:
    """
    Update a user's role in a team.

    Args:
        team_id (UUID): The ID of the team.
        user_id (UUID): The ID of the user.
        role (str): The new role for the user in the team.
        db (Session): The database session.

    Returns:
        UserTeamOutput: The updated user-team association.

    Raises:
        HTTPException: If there's an error updating the role.
    """
    user_team_service = get_user_team_service(db)
    return user_team_service.update_user_role_in_team(user_id, team_id, role)


@router.get(
    "/{team_id}",
    response_model=TeamOutput,
    summary="Get a team by ID",
    description="Retrieve a team using its unique identifier",
    responses={
        200: {"description": "Team retrieved successfully"},
        404: {"description": "Team not found"},
        500: {"description": "Internal server error"},
    },
)
def get_team(team_id: UUID, db: Session = Depends(get_db)) -> TeamOutput:
    """
    Get a team by its ID.

    Args:
        team_id (UUID): The ID of the team to retrieve.
        db (Session): The database session.

    Returns:
        TeamOutput: The retrieved team.

    Raises:
        HTTPException: If the team is not found.
    """
    team_service = get_team_service(db)
    team = team_service.get_team_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return team


@router.put(
    "/{team_id}",
    response_model=TeamOutput,
    summary="Update a team",
    description="Update an existing team with the provided input data",
    responses={
        200: {"description": "Team updated successfully"},
        404: {"description": "Team not found"},
        400: {"description": "Invalid input data"},
        500: {"description": "Internal server error"},
    },
)
def update_team(team_id: UUID, team_update: TeamInput, db: Session = Depends(get_db)) -> TeamOutput:
    """
    Update a team.

    Args:
        team_id (UUID): The ID of the team to update.
        team_update (TeamInput): The updated team data.
        db (Session): The database session.

    Returns:
        TeamOutput: The updated team.

    Raises:
        HTTPException: If the team is not found.
    """
    team_service = get_team_service(db)
    team = team_service.update_team(team_id, team_update)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return team


@router.delete(
    "/{team_id}",
    response_model=bool,
    summary="Delete a team",
    description="Delete a team using its unique identifier",
    responses={
        200: {"description": "Team deleted successfully"},
        404: {"description": "Team not found"},
        500: {"description": "Internal server error"},
    },
)
def delete_team(team_id: UUID, db: Session = Depends(get_db)) -> bool:
    """
    Delete a team.

    Args:
        team_id (UUID): The ID of the team to delete.
        db (Session): The database session.

    Returns:
        bool: True if the team was successfully deleted, False otherwise.
    """
    team_service = get_team_service(db)
    return team_service.delete_team(team_id)


@router.get(
    "",
    response_model=list[TeamOutput],
    summary="List all teams",
    description="Retrieve a list of all teams with pagination",
    responses={200: {"description": "Teams retrieved successfully"}, 500: {"description": "Internal server error"}},
)
def list_teams(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)) -> list[TeamOutput]:
    """
    List teams with pagination.

    Args:
        skip (int, optional): The number of teams to skip. Defaults to 0.
        limit (int, optional): The maximum number of teams to return. Defaults to 100.
        db (Session): The database session.

    Returns:
        List[TeamOutput]: A list of teams.
    """
    team_service = get_team_service(db)
    return team_service.list_teams(skip, limit)


@router.get(
    "/{team_id}/users",
    response_model=list[UserTeamOutput],
    summary="Get team users",
    description="Get all users associated with a team",
    responses={
        200: {"description": "Successfully retrieved team users"},
        404: {"description": "Team not found"},
        500: {"description": "Internal server error"},
    },
)
def get_team_users(team_id: UUID, db: Session = Depends(get_db)):
    service = UserTeamService(db)
    return service.get_team_users(team_id)


@router.post(
    "/{team_id}/users",
    response_model=UserTeamOutput,
    summary="Add user to team",
    description="Add a user to a specific team",
    responses={
        201: {"description": "User added to team successfully"},
        400: {"description": "Invalid input data"},
        404: {"description": "Team or user not found"},
        500: {"description": "Internal server error"},
    },
)
def add_user_to_team(team_id: UUID, user_team_input: UserTeamInput, db: Session = Depends(get_db)) -> UserTeamOutput:
    """
    Add a user to a team.

    Args:
        team_id (UUID): The ID of the team.
        user_team_input (UserTeamInput): The input data for adding a user to the team.
        db (Session): The database session.

    Returns:
        UserTeamOutput: The user-team association.

    Raises:
        HTTPException: If the team or user is not found.
    """
    user_team_service = get_team_service(db)
    try:
        return user_team_service.add_user_to_team(user_team_input.user_id, user_team_input.team_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
