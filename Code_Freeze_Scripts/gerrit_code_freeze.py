import argparse
import subprocess
import os.path
import os
from contextlib import contextmanager
from multiprocessing import Pool
from functools import partial
import time
GERRIT_URL = 'ssh://gerrit-epk.seli.gic.ericsson.se:29418'
REPOSITORY_BASE_PATH = 'src'
GIT = '/proj/env/bin/git'
RULES_FILENAME = 'rules.pl'
# Prolog code snippets
FACTS = '% Facts\n'
CODE_FREEZE_APPROVER = 'code_freeze_approver(user({0})).\n'
CODE_FREEZE_BRANCH = "code_freeze_branch('refs/heads/{0}').\n"
CODE_FREEZE_RULES = \
    '''
% Rules
submit_rule(S) :-
  gerrit:change_branch(B), code_freeze_branch(B), !,
  gerrit:default_submit(X), X =.. [submit | Ls],
  add_code_freeze_approval(Ls, R), S =.. [submit | R].
submit_rule(S) :-
  gerrit:default_submit(S).
'''
CODE_FREEZE_APPROVAL_RULE = \
    '''
add_code_freeze_approval(S1, S2) :-
  gerrit:commit_label(label('Code-Review', 2), A), code_freeze_approver(A), !,
  S2 = [label('Code-Freeze-Submit-Approval', ok(A)) | S1].
add_code_freeze_approval(S1, [label('Code-Freeze-Submit-Approval', need(_)) | S1]).
'''
def _perform_code_freeze_for_repository(obj, arg):
    """
    Alias for instance method that allows the method to be called in a
    multiprocessing pool
    """
    return obj.perform_code_freeze_for_repository(arg)
def is_empty(container):
    return len(container) == 0
@contextmanager
def pool_context_manager(pool):
    """
    Context management protocol is not supported by the Pool class in
    Python version 3.2 or lower. When Python 3.3 or later is used this
    function can be removed.
    :param pool: A Pool object
    """
    try:
        yield pool
    finally:
        pool.close()
class GerritCodeFreeze:
    def __init__(self, command_line_arguments):
        self.log_data = ''
        self.repositories = set(command_line_arguments.repositories)
        self.approvers = set(command_line_arguments.approvers)
        self.branch_freeze = set(command_line_arguments.branch_freeze)
        self.branch_un_freeze = set(command_line_arguments.branch_un_freeze)
        self.processes = command_line_arguments.processes
        self.gerrit_url = command_line_arguments.gerrit
        self.git = command_line_arguments.git
        self.debug_mode = command_line_arguments.debug
        self.start_path = os.getcwd()
        self.repository_frozen_branches = []
        self.branches_to_freeze = []
        self.branches_to_un_freeze = []
        self._verify_uniqueness_for_freeze_and_un_freeze_branches()
        self._found_error = False
    def _verify_uniqueness_for_freeze_and_un_freeze_branches(self):
        non_unique_branches = [branch for branch in self.branch_freeze if branch in self.branch_un_freeze]
        if not is_empty(non_unique_branches):
            raise Exception('Found same branch to freeze and unfreeze: ' + ' '.join(non_unique_branches))
    def perform_code_freeze(self):
        start_time = time.time()
        if not self.debug_mode:
            self._freeze_with_multi_processes()
        else:
            self._freeze_with_single_process()
        end_time = time.time()
        print 'Time spent: {0:.2f}s'.format(end_time - start_time)
        if self._found_error:
            return False, 'At least one sub process got ERROR'
        return True, 'All OK'
    def _freeze_with_multi_processes(self):
        """
        Used this method for normal operations to speed up the execution time.
        """
        _bound_instance_method_alias = partial(_perform_code_freeze_for_repository, self)
        with pool_context_manager(Pool(processes=self.processes)) as pool:
            for result, error_message in pool.imap_unordered(_bound_instance_method_alias, self.repositories, 1):
                self._handle_process_result(result, error_message)
        pool.join()
    def _freeze_with_single_process(self):
        """
        Use this method for easier debugging of possible issues in child processes
        """
        for repository in self.repositories:
            result, error_message = self.perform_code_freeze_for_repository(repository)
            self._handle_process_result(result, error_message)
    def perform_code_freeze_for_repository(self, repository):
        """
        All data changed in the object from this point forward will only be change for the
        current process. I.e. only one repository handled in this method and all its
        sub-methods.
        :param repository: The name of the repository
        :return: The logging and output from git commands for the repository
        """
        try:
            self._log('* ' + repository + ' *')
            self._checkout_repositories(repository)
            self._set_rules_for_repositories(repository)
            self._create_commit_and_push_to_repositories(repository)
        except (subprocess.CalledProcessError, OSError) as e:
            return e, self.log_data
        except Exception as e:
            return e
        return self.log_data, None
    def _checkout_repositories(self, repository):
        """
        Handles checkout for one repository
        :param repository: The name of the repository
        """
        os.chdir(self.start_path)
        self._log('Getting repository: ' + repository)
        repository_path = REPOSITORY_BASE_PATH + '/' + repository
        if self._is_repository_already_checkout(repository_path):
            self._create_src_directory_if_needed()
            self._clone_repository(repository, repository_path)
        self._get_latest_changes(repository_path)
        os.chdir(self.start_path)
    def _is_repository_already_checkout(self, repository_path):
        return not os.path.exists(repository_path + '/.git')
    def _create_src_directory_if_needed(self):
        """
        Creates the "src" directory if needed. The reason for the inverted
        operations below, is to avoid a possible race condition. When
        Python 3.4+ is available, this method can be replaced with
        os.makedirs(path, exist_ok=True)
        """
        try:
            os.makedirs(REPOSITORY_BASE_PATH)
        except OSError:
            if not os.path.isdir(REPOSITORY_BASE_PATH):
                raise
    def _clone_repository(self, repository_to_clone, repository_target_path):
        self._log('Cloning repository ' + repository_to_clone + ' to target path ' + repository_target_path)
        self._check_output([self.git, 'clone', '-n', self.gerrit_url + '/' + repository_to_clone, repository_target_path])
        os.chdir(repository_target_path)
        self._log('Current path: ' + os.getcwd())
        self._log('Fetch and checkout meta/config')
        self._check_output([self.git, 'fetch', 'origin', 'meta/config:config'])
        self._check_output([self.git, 'checkout', 'config'])
    def _get_latest_changes(self, local_repository_path):
        if not os.getcwd().endswith(local_repository_path):
            os.chdir(local_repository_path)
        self._log('Fetch and reset meta/config')
        self._check_output([self.git, 'fetch', 'origin', 'meta/config:cfg'])
        self._check_output([self.git, 'reset', '--hard', 'cfg'])
    def _set_rules_for_repositories(self, repository):
        self._change_to_repository_directory(repository)
        if os.path.exists(RULES_FILENAME):
            self._find_frozen_branches()
        self._aggregate_branches_to_freeze_and_un_freeze()
        if not is_empty(self.branches_to_freeze):
            self._write_rules_to_file_for_repository()
    def _find_frozen_branches(self):
        with open(os.path.join(os.getcwd(), RULES_FILENAME), 'r') as rules_file:
            for line in rules_file:
                self._if_branch_found_add_to_frozen(line)
    def _if_branch_found_add_to_frozen(self, line):
        if not line.find('refs/heads/') == -1:
            branch = line.split('refs/heads/').pop().split("'")[0]
            self._log('Found frozen branch: ' + branch)
            if is_empty(self.repository_frozen_branches):
                self.repository_frozen_branches = [branch]
            else:
                self.repository_frozen_branches.append(branch)
    def _aggregate_branches_to_freeze_and_un_freeze(self):
        self._set_branches_to_freeze()
        self._set_branches_to_un_freeze()
    def _set_branches_to_freeze(self):
        self.branches_to_freeze = list(self.branch_freeze)
        for frozen_branch in self.repository_frozen_branches:
            if frozen_branch not in self.branches_to_freeze:
                self.branches_to_freeze.append(frozen_branch)
    def _set_branches_to_un_freeze(self):
        for un_freeze_branch in self.branch_un_freeze:
            if un_freeze_branch in self.branches_to_freeze:
                self.branches_to_freeze.remove(un_freeze_branch)
                if is_empty(self.branches_to_un_freeze):
                    self.branches_to_un_freeze = [un_freeze_branch]
                else:
                    self.branches_to_un_freeze.append(un_freeze_branch)
    def _write_rules_to_file_for_repository(self):
        file_path = os.path.join(os.getcwd(), RULES_FILENAME)
        if os.path.exists(file_path):
            os.remove(file_path)
        with open(file_path, 'w') as rules_file:
            rules_file.write(FACTS)
            for approver in self.approvers:
                rules_file.write(CODE_FREEZE_APPROVER.format(approver))
            for branch in self.branches_to_freeze:
                rules_file.write(CODE_FREEZE_BRANCH.format(branch))
            rules_file.write(CODE_FREEZE_RULES)
            rules_file.write(CODE_FREEZE_APPROVAL_RULE)
    def _create_commit_and_push_to_repositories(self, repository):
        self._log('To Freeze: {0}'.format(self.branches_to_freeze))
        self._log('To unFreeze: {0}'.format(self.branches_to_un_freeze))
        self._change_to_repository_directory(repository)
        if not is_empty(self.branches_to_freeze) and self._has_changed_been_made_in_repository():
            self._log('*** Freeze/Unfreeze branches has changed for repository ' + repository)
            self._check_output([self.git, 'add', RULES_FILENAME])
        elif not is_empty(self.branches_to_un_freeze) and os.path.exists(RULES_FILENAME):
            self._log('*** Unfreeze all for repository ' + repository + ', thus remove the rules.pl')
            self._check_output([self.git, 'rm', '-f', RULES_FILENAME])
        else:
            self._log('*** Nothing to do for repository ' + repository)
            return
        if self._has_changed_been_made_in_repository():
            commit_title, commit_body = self._commit_message()
            self._check_output([self.git, 'commit', '-m', commit_title, '-m', commit_body])
            self._check_output([self.git, 'push', 'origin', 'config:meta/config'])
    def _change_to_repository_directory(self, repository):
        os.chdir(self.start_path + '/' + REPOSITORY_BASE_PATH + '/' + repository)
    def _has_changed_been_made_in_repository(self):
        git_status = self._check_output([self.git, 'status'])
        if RULES_FILENAME in git_status:
            return True
        else:
            return False
    def _commit_message(self):
        if not is_empty(self.branches_to_freeze) and is_empty(self.branches_to_un_freeze):
            body = 'Branches frozen:\n' + '\n'.join(self.branches_to_freeze)
            return 'Code Freeze for branche(s)', body
        elif not is_empty(self.branches_to_freeze) and not is_empty(self.branches_to_un_freeze):
            body = 'Branches frozen:\n' + '\n'.join(self.branches_to_freeze) + \
                   '\n\nBranches unfrozen:\n' + '\n'.join(self.branches_to_un_freeze)
            return 'Code Freeze and UnFreeze for branche(s)', body
        elif is_empty(self.branches_to_freeze) and not is_empty(self.branches_to_un_freeze):
            body = 'Branches unfrozen:\n' + '\n'.join(self.branches_to_un_freeze)
            return 'Code UnFreeze for branche(s)', body
    def _check_output(self, command):
        self._log('> ' + ' '.join(command))
        try:
            result = subprocess.check_output(command, stderr=subprocess.STDOUT)
            self._log(result)
            return result
        except subprocess.CalledProcessError as e:
            self._log('!! Error:\n' + e.output)
            raise
        except OSError as e:
            self._log('!! Error:\n' + e.strerror)
            raise
    def _handle_process_result(self, result, error_message):
        if isinstance(result, str):
            print result
        elif isinstance(result, subprocess.CalledProcessError):
            self._found_error = True
            if error_message is not None:
                print error_message
            print result.output
        elif isinstance(result, Exception):
            self._found_error = True
            if error_message is not None:
                print error_message
            print result.message
            print result
    def _log(self, string):
        self.log_data = self.log_data + '\n' + string
def main():
    parser = argparse.ArgumentParser(description='Gerrit code freezer')
    parser.add_argument('--repositories', nargs='+', action='store', dest='repositories', required=True,
                        help="The repositories (' '-separated) to freeze/unfreeze")
    parser.add_argument('--approvers', nargs='+', action='store', dest='approvers', required=True,
                        help="The numeric gerrit-id's (' '-separated) of the users with approve rights")
    parser.add_argument('--branch-freeze', nargs='*', action='store', dest='branch_freeze', required=True,
                        help="The branches to freeze (' '-separated)")
    parser.add_argument('--branch-un-freeze', nargs='*', action='store', dest='branch_un_freeze', required=True,
                        help="The branches to release (' '-separated)")
    parser.add_argument('--processes', type=int, default=8,
                        help='Number of processes to use for handling repositories (default: %(default)s)')
    parser.add_argument('--gerrit', default=GERRIT_URL, action='store',
                        help="Set the Gerrit server URL with it's port. Defaults to: {0}".format(GERRIT_URL))
    parser.add_argument('--git', default=GIT, action='store',
                        help="The path to the git binary since installation directory might vary between developer and automation machines. Defaults to: {0}".format(GIT))
    parser.add_argument('--debug', default=False, action='store_true',
                        help='Runs the script in single process mode for easier debugging.')
    arguments = parser.parse_args()
    print arguments
    print 'Current path: ' + os.getcwd()
    gerrit_code_freeze = GerritCodeFreeze(arguments)
    exit_ok, exit_string = gerrit_code_freeze.perform_code_freeze()
    if not exit_ok:
        exit(exit_string)
if __name__ == '__main__':
    main()
