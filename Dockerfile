FROM python:3.8-bookworm
MAINTAINER Frank Bertsch <frank@mozilla.com>

# Guidelines here: https://github.com/mozilla-services/Dockerflow/blob/main/docs/building-container.md
ARG RUST_SPEC=stable
ARG USER_ID="10001"
ARG GROUP_ID="app"
ARG HOME="/app"

ENV HOME=${HOME}
RUN groupadd --gid ${USER_ID} ${GROUP_ID} && \
    useradd --create-home --uid ${USER_ID} --gid ${GROUP_ID} --home-dir /app ${GROUP_ID}

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        file gcc tree libwww-perl && \
    apt-get autoremove -y && \
    apt-get clean

# Install Rust and Cargo
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain=${RUST_SPEC}

ENV CARGO_INSTALL_ROOT=${HOME}/.cargo
ENV PATH ${PATH}:${HOME}/.cargo/bin

# Install a tagged version of jsonschema-transpiler
RUN cargo install jsonschema-transpiler --version 2.0.0

# Upgrade pip
RUN pip install --upgrade pip

WORKDIR ${HOME}

# Recursively change ownership of the application folder to the user;
# this takes a while, so we put this step before copying in code.
RUN chown -R ${USER_ID}:${GROUP_ID} ${HOME}

COPY --chown=${USER_ID}:${GROUP_ID} requirements requirements/
RUN pip install -r requirements/requirements.txt
RUN pip install -r requirements/test_requirements.txt

COPY --chown=${USER_ID}:${GROUP_ID} . ${HOME}/mozilla-schema-generator
ENV PATH $PATH:${HOME}/mozilla-schema-generator/bin

RUN pip install --no-dependencies -e ${HOME}/mozilla-schema-generator

# Drop root
USER ${USER_ID}

ENTRYPOINT ["schema_generator.sh"]
