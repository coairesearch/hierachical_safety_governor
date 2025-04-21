import orchestrator, argparse; p=argparse.ArgumentParser(); p.add_argument("--config"); a=p.parse_args(); orchestrator.main(a.config)
