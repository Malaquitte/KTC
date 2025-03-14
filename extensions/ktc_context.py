def check_tool_endstop_configuration(ktc_instance):
    """
    Vérifie la cohérence entre les états des endstops de toolchanger et des docks d'outils.
    
    Cette fonction vérifie que:
    1. Si un outil est détecté sur le toolchanger, exactement un outil doit être absent du rack
    2. Si aucun outil n'est détecté sur le toolchanger, tous les outils doivent être présents sur le rack
    3. Si tous les outils sont sur le rack, aucun outil ne doit être détecté sur le toolchanger
    
    Retourne:
    - tuple(bool, str): (configuration_valide, message_erreur)
    """
    # Noms des endstops (ces noms doivent correspondre à vos définitions dans la configuration)
    toolchanger_endstop = "manual_stepper tchead_endstop"
    dock_endstops = ["manual_stepper t0dock_endstop", "manual_stepper t1dock_endstop"]
    
    # Fonction pour obtenir l'état d'un endstop
    def get_endstop_state(endstop_name):
        try:
            # Extraire le nom du stepper manuel
            stepper_parts = endstop_name.split()
            if len(stepper_parts) >= 2:
                stepper_name = " ".join(stepper_parts[:2])
            else:
                stepper_name = endstop_name
                
            # Récupérer l'objet stepper et son état d'endstop
            manual_stepper = ktc_instance.printer.lookup_object(stepper_name)
            endstop_state = manual_stepper.get_status(ktc_instance.printer.get_reactor().monotonic())["endstop_state"]
            
            # True = endstop déclenché (détection)
            return endstop_state
        except Exception as e:
            ktc_instance.log.always(f"Erreur lors de la lecture de l'endstop {endstop_name}: {str(e)}")
            return None
    
    # Récupérer les états des endstops
    tc_state = get_endstop_state(toolchanger_endstop)
    dock_states = {dock: get_endstop_state(dock) for dock in dock_endstops}
    
    # Si un endstop n'a pas pu être lu, retourner une erreur
    if tc_state is None or None in dock_states.values():
        return False, "Impossible de lire tous les états d'endstops"
    
    # Compter combien d'outils sont absents de leurs docks
    tools_off_dock = sum(1 for state in dock_states.values() if state is False)
    
    # Analyser la configuration
    if all(dock_states.values()) and tc_state is True:
        # Cas 1: Tous les outils sont sur les docks mais le toolchanger indique qu'un outil est attaché
        error_msg = "Tous les outils sont sur leurs docks mais le toolchanger indique qu'un outil est attaché"
        ktc_instance.log.always(f"ERREUR ENDSTOPS: {error_msg}")
        return False, error_msg
        
    elif tc_state is True and tools_off_dock != 1:
        # Cas 2: Le toolchanger a un outil, mais le nombre d'outils absents n'est pas exactement 1
        error_msg = f"Le toolchanger a un outil, mais {tools_off_dock} outils sont absents de leurs docks (devrait être exactement 1)"
        ktc_instance.log.always(f"ERREUR ENDSTOPS: {error_msg}")
        return False, error_msg
        
    elif tc_state is False and tools_off_dock > 0:
        # Cas 3: Le toolchanger n'a pas d'outil, mais certains outils sont absents de leurs docks
        error_msg = f"Le toolchanger n'a pas d'outil, mais {tools_off_dock} outils sont absents de leurs docks"
        ktc_instance.log.always(f"ERREUR ENDSTOPS: {error_msg}")
        return False, error_msg
    
    # Si nous arrivons ici, la configuration est valide
    if tools_off_dock == 0:
        ktc_instance.log.trace("ENDSTOPS OK: Tous les outils sont sur leurs docks et le toolchanger est vide")
    else:
        missing_docks = [dock for dock, state in dock_states.items() if state is False]
        ktc_instance.log.trace(f"ENDSTOPS OK: L'outil du dock {missing_docks[0]} est attaché au toolchanger")
    
    return True, "Configuration des endstops valide"