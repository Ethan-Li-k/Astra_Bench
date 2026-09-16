"""Disambiguate native object identifiers without changing sampled geometry."""
from copy import copy


def unique_object_labels(actors):
    from simple.core.actor import ObjectActor
    from simple.core.object import SemanticAnnotated

    objects = [(key, actor) for key, actor in actors.items()
               if isinstance(actor, ObjectActor)]
    labels = {key: actor.asset.label if isinstance(actor.asset, SemanticAnnotated)
              else actor.asset.uid for key, actor in objects}
    reserved = set(labels.values())
    seen = set()
    changes = []
    # Preserve names used by native target/container reward code.
    objects.sort(key=lambda item: (item[0] not in ('target', 'container'),
                                   item[0] != 'target'))
    for key, actor in objects:
        label = labels[key]
        if label not in seen:
            seen.add(label)
            continue
        # Native reward code sometimes uses substring matching on body names.
        # A prefix such as apple__distractor would still match target "apple".
        index = 0
        candidate = f'rsi_aux_{index:04d}'
        while candidate in reserved:
            index += 1
            candidate = f'rsi_aux_{index:04d}'
        if any(original in candidate for original in labels.values()):
            raise ValueError('Cannot safely disambiguate native reward-name substrings')
        reserved.add(candidate)
        # Asset managers share cached instances; never mutate those instances.
        actor.asset = copy(actor.asset)
        field = 'label' if isinstance(actor.asset, SemanticAnnotated) else 'uid'
        setattr(actor.asset, field, candidate)
        changes.append({'actor': key, 'original': label, 'identifier': candidate})
    return changes


def install_unique_object_labels(env):
    engine = env.unwrapped.mujoco
    original = engine._setup_scene

    def setup(**kwargs):
        engine.rsi_object_identifier_changes = unique_object_labels(
            engine.task.layout.actors)
        return original(**kwargs)

    engine._setup_scene = setup
