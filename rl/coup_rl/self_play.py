import logging
import re
import gym
import gym_coup
from coup_rl.qtable import QTable
from coup_rl.agent import Agent
from coup_rl.utils import get_num_changed, has_converged

logging.basicConfig()
logger = logging.getLogger('coup_rl')

class SelfPlay:
    def __init__(self,
                 filepath,
                 learning_rate=None,
                 discount_factor=None,
                 epsilon=None,
                 log_level=None):
        '''
        filepath:        Path for file ending in .npz
        learning_rate:   Float (0, 1]
        discount_factor: Float [0, 1]
        epsilon:         Float [0, 1]
        log_level:       coup_rl log level

        Must supply lr, df, eps when creating new table.
        Otherwise, supplying them replaces params in existing file.
        '''
        # Load from
        self.filepath = filepath
        self.last_file = None # Updated below if existing file
        # and get the base name to save to later
        fp_split = filepath.split('/')
        file = fp_split[-1]
        suf = re.search('_\d\d\d\d\d\d\d\d\d\d.npz', file)
        if suf:
            start = suf.start() + 1
            end = suf.end() - 4
            self.start_ep = int(file[start:end])
            file = file[:start]
        else:
            # When creating new, user likely wont enter number
            # But .npz will be there
            self.start_ep = 0
            file = file[:-4] + '_'
        fp_split[-1] = file
        self.filepath_no_suf = '/'.join(fp_split)
        # Full filepath except episode num and .npz

        # Make the gym env
        self.env = gym.make('coup-v0')

        if log_level is not None:
            logger.setLevel(log_level)

        # Try to load existing Q Table
        try:
            self.qtable = QTable()
            self.qtable.load(self.filepath)
            self.last_file = self.filepath

            # Update the params mid-training if supplied
            if learning_rate is not None:
                self.qtable.learning_rate = learning_rate
            if discount_factor is not None:
                self.qtable.discount_factor = discount_factor
            if epsilon is not None:
                self.qtable.epsilon = epsilon
        except FileNotFoundError:
            if (learning_rate is not None and
                discount_factor is not None and
                epsilon is not None):
                # Create new Q Table
                shape = (15, 15, 4, 4, 13, 13, self.env.action_space.n - 7)
                self.qtable = QTable(shape, learning_rate, discount_factor, epsilon)
            else:
                raise RuntimeError('Agent file does not exist, and not enough information was provided to create a new agent')

        self.p1 = Agent(1, self.env, self.qtable)
        self.p2 = Agent(2, self.env, self.qtable)

    def train(self, episodes, checkpoint, conv_eps):
        '''
        episodes:   Number of episodes to run
        checkpoint: Number of episodes to save a new agent file after
        conv_eps:   Convergence epsilon. Max difference for convergence
        '''
        ep = 1
        converged = False
        while ep <= episodes and not converged:
            self.env.reset()
            self.run_game()

            if ep % checkpoint == 0 or ep == episodes:
                logger.info(f'Saving at checkpoint. Episode {ep} / {episodes}')

                # Comparison metrics
                if self.last_file is not None:
                    # Use prev table
                    qold = QTable()
                    qold.load(self.last_file)
                    num_changed = get_num_changed(qold.table, self.qtable.table)
                    logger.info(f'\tNum Q-values modified: {num_changed}')
                    converged = has_converged(qold.table, self.qtable.table, conv_eps)
                    if converged:
                        logger.info('Converged')

                num_ep = str(self.start_ep + ep)
                num_ep = (10-len(num_ep)) * '0' + num_ep
                self.last_file = self.filepath_no_suf + num_ep + '.npz'
                self.qtable.save(self.last_file)

            ep += 1

    def run_game(self):
        '''
        Run a single Coup game
        '''
        done = False
        whose_action = 0
        while not done:
            # P1 turn
            while not done and whose_action != 1:
                obs, reward, done, info = self.p1.step()
                self.p2.reward -= reward # Make sure the other agent gets feedback for what happened
                self.env.render()
                whose_action = obs[-1]
            # P2 turn
            while not done and whose_action != 0:
                obs2, reward2, done, info2 = self.p2.step()
                self.p1.reward -= reward2 # Make sure the other agent gets feedback for what happened
                self.env.render()
                whose_action = obs2[-1]

        # Do a final update now that the game is over
        self.p1.update_q_value(0)
        self.p2.update_q_value(0)
