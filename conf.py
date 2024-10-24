from hydra import initialize, compose
from typing import Any
import os
from omegaconf import OmegaConf, DictConfig
import copy
import asyncio  
# Définissez une liste de chemins de configuration
config_paths = [
    ".hydra-conf",
    ".hydra-conf/services",
]

initialize(config_path=config_paths[0], version_base="1.1")

class cfg_instance(dict):
    def __init__(self, cfg_name: str):

        cfg = compose(config_name=cfg_name, overrides=[f"+config_path={path}" for path in config_paths[1:]])
        self.cfg = OmegaConf.create(cfg)
        OmegaConf.resolve(self.cfg)
        self.contexte = []
        self.cursor = copy.deepcopy(self.cfg)

    def __call__(self, *args: Any, **kwds: Any) -> DictConfig:
        if self.contexte:
            return self.cursor
        else:
            return self.cfg
    
    def __getcontext__(self):
        for key in self.contexte:
            try:
                cursor = getattr(self.cursor, key)
            except Exception as e:
                raise e
        return cursor

    def start(self) -> None:
        self.contexte = []

    def walk(self,*args:list[str])->None:
        self.contexte.extend(args)
        self.cursor = self.__getcontext__()
        return self

    def __setitem__(self, key:str, value:DictConfig ) -> None:
        if self.contexte:
            self.cursor[key] = value
        else:
            self.cfg[key] = value

    def __getitem__(self, key:str) -> DictConfig:
        if self.contexte:
            return self.cursor[key]
        else:
            return self.cfg[key]
    def get(self, key:str)->DictConfig:
        return self.cursor[key]

    def __getattribute__(self, key: str) -> DictConfig:
        try:
            test = object.__getattribute__(self, key)
            if asyncio.iscoroutinefunction(test):
                return test 
            return test
        except AttributeError:
            cursor = object.__getattribute__(self, 'cursor')
            contexte = object.__getattribute__(self, 'contexte')
            
            if contexte:
                for ctx_key in contexte:
                    cursor = getattr(cursor, ctx_key)
            
            if key in cursor:
                return getattr(cursor, key)
            else:
                raise AttributeError(f"L'attribut '{key}' n'existe pas")

    def __enter__(self):
        return self

    def __exit__(self):
        self.cursor = self.cfg
        self.contexte = []

    def add_prefix(self, prefix:str):
        """
        Décorateur qui ajoute un préfixe à toutes les clés de configuration qui ne commencent pas déjà par ce préfixe.

        Args:
            prefix (str): Le préfixe à ajouter aux clés de configuration.

        Returns:
            function: Le décorateur qui enveloppe la fonction originale.

        Le décorateur modifie la configuration en ajoutant de nouvelles clés préfixées,
        tout en préservant les clés originales. Les nouvelles clés préfixées sont ajoutées
        à la liste `self.prefixes`.
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                new_keys = []
                for key, value in self.cfg.items():
                    if not key.startswith(prefix):
                        new_key = f"{prefix}.{key}"
                        self.cfg[new_key] = value
                        new_keys.append(new_key)
                self.prefixes.extend(new_keys)
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def get_cfg(self):
        return self.cfg
    
    def __repr__(self):
        return OmegaConf.to_yaml(self.cfg)
    
    def __str__(self):
        return OmegaConf.to_yaml(self.cfg)
    
    def __bool__(self):
        return bool(self.cfg)