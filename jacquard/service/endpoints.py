"""Built-in, core HTTP endpoints."""

from .base import Endpoint

from jacquard.users import get_settings
from jacquard.users.settings import branch_hash
from jacquard.experiments import Experiment


class Root(Endpoint):
    """
    API root.

    Essentially a directory of the main endpoints available.
    """

    url = '/'

    def handle(self):
        """Dispatch request."""
        return {
            'users': self.reverse('user', user=':user'),
            'experiments': self.reverse('experiments-overview'),
        }


class User(Endpoint):
    """
    User settings lookup.

    Gets the JSON representation of the current experiment settings for a
    given user ID.
    """

    url = '/users/<user>'

    def handle(self, user):
        """Dispatch request."""
        settings = get_settings(
            user,
            self.config.storage,
            self.config.directory,
        )

        return {**settings, 'user': user}


class ExperimentsOverview(Endpoint):
    """
    Experiment status overview.

    Gives basic details on all experiments in the system, regardless of state.
    """

    url = '/experiments'

    def handle(self):
        """Dispatch request."""
        with self.config.storage.transaction() as store:
            active_experiments = store.get('active-experiments', ())
            experiments = list(Experiment.enumerate(store))

        return [
            {
                'id': experiment.id,
                'url': self.reverse('experiment', experiment=experiment.id),
                'state':
                    'active'
                    if experiment.id in active_experiments
                    else 'inactive',
                'name': experiment.name,
            }
            for experiment in experiments
        ]


class ExperimentDetail(Endpoint):
    """
    Full experiment details.

    Includes all users in each branch.
    """

    url = '/experiments/<experiment>'

    def handle(self, experiment):
        """Dispatch request."""
        with self.config.storage.transaction() as store:
            experiment_config = Experiment.from_store(store, experiment)

        branch_ids = [branch['id'] for branch in experiment_config.branches]
        branches = {x: [] for x in branch_ids}

        for user_entry in self.config.directory.all_users():
            if not experiment_config.includes_user(user_entry):
                continue

            branch_id = branch_ids[
                branch_hash(experiment, user_entry.id) %
                len(branch_ids)
            ]

            branches[branch_id].append(user_entry.id)

        return {
            'id': experiment_config.id,
            'name': experiment_config.name,
            'launched': str(experiment_config.launched),
            'concluded': str(experiment_config.concluded),
            'branches': branches,
        }