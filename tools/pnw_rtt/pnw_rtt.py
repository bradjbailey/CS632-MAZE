import os
import sys
import csv
import logging
import argparse
sys.path.append(os.path.abspath(".."))
sys.path.append(os.path.abspath("../../rtt_simulator"))
sys.path.append(os.path.abspath("../../satgenpy"))

from sim_config import SimulationConfig
from helper import PNWMixedNetworkPathRTTSimulator, PNWMixedNetworkEveryPairRTTSimulator, retrieve_network_state, generate_network_state

def read_options():
    parser = argparse.ArgumentParser(description="Simulate RTT time for a mixed ground-satellite network in the PNW")
    parser.add_argument("-g", "--gen-state", action="store_true", help="generate the required network state")
    parser.add_argument("-r", "--run", action="store_true", help="run simulation")
    parser.add_argument("-a", "--all-pairs", action="store_true", help="Calculate RTT between all pairs of nodes not just a simple path")
    parser.add_argument("config", type=str, help="simulation config file")
    parser.add_argument("path", type=str, help="folder to run simulation in and store generated state")
    parser.add_argument("lambd", type=float, help="poisson parameter for network load (new calls/sec)")
    parser.add_argument("userType", type=str, help="User type, one of {govt, senior, normal}")

    args = parser.parse_args()
    return args

def main():
    args = read_options()
    config_path = os.path.abspath(args.config)
    sim_path = os.path.abspath(args.path)

    l = args.lambd
    if l >= 0.5:
      l = 0.5
    elif l >= 0.42:
      l = 0.42
    elif l >= 0.35:
      l = 0.35
    elif l >= 0.27:
      l = 0.27
    elif l >= 0.21:
      l = 0.21
    else:
      l = 0.15

    try:
        config = SimulationConfig(config_path)
    except ValueError as e:
        logging.error("Failed to load simulation config file '" + config_path + "' -> " + str(e))
        return

    if not os.path.exists(sim_path):
        os.mkdir(sim_path)


    if args.gen_state:
        try:
            generate_network_state(config, sim_path)
        except ValueError as e:
            logging.error("Failed to generate network state -> " + str(e))
            return

    if args.run:
        try:
            gs_map = retrieve_network_state(config, sim_path)
        except ValueError as e:
            logging.error("Failed to retrieve satellite network state -> " + str(e))
            return

        simulation_configs = config.sub_simulations()
        for sub_config_name in simulation_configs:
            sub_config = simulation_configs[sub_config_name]
            logging.info("Calculating Round Trip Time for specified mixed-network path...")
            rtt_file_path = sim_path + "/" + sub_config.name() + "_" + args.userType + "_l" + str(l) + "_calculated_rtts.txt"
            simulator = None
            if args.all_pairs:
                simulator = PNWMixedNetworkEveryPairRTTSimulator(sub_config, sim_path, gs_map)
            else:
                simulator = PNWMixedNetworkPathRTTSimulator(sub_config, sim_path, gs_map)

            avg_rtt = [0 for _ in range(len(simulator.get_param_order()))]
            try:
                with open(rtt_file_path, 'w') as fp:
                    writer = csv.writer(fp)
                    writer.writerow(["timestep"] + list(simulator.get_param_order()))
                    i = 0
                    for rtt in simulator.generate_rtts(lambd = l, userType = args.userType):
                        for i in range(len(rtt)):
                            avg_rtt[i] += rtt[i]
                        writer.writerow([i] + list(rtt))
                        i += 1
                logging.info("Simulation results written to " + rtt_file_path)
            except OSError as e:
                logging.error("Failed to write simulation results to " + rtt_file_path + " -> " + str(e))
                return


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
