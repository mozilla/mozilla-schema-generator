FROM python:3.7
MAINTAINER Frank Bertsch <frank@mozilla.com>

# Guidelines here: https://github.com/mozilla-services/Dockerflow/blob/master/docs/building-container.md
ARG RUST_SPEC=stable
ARG USER_ID="10001"
ARG GROUP="app"
ARG HOME="/app"

ENV HOME=${HOME}
RUN mkdir ${HOME} && \
    chown ${USER_ID}:${USER_ID} ${HOME} && \
    groupadd --gid ${USER_ID} ${GROUP} && \
    useradd --no-create-home --uid 10001 --gid 10001 --home-dir /app ${GROUP}

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        file gcc libwww-perl jq && \
    apt-get autoremove -y && \
    apt-get clean

# Install Google Cloud SDK
RUN curl -sSL https://sdk.cloud.google.com | bash
ENV PATH $PATH:$HOME/google-cloud-sdk/bin

# Install Rust and Cargo
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain=${RUST_SPEC}

ENV CARGO_INSTALL_ROOT=${HOME}/.cargo
ENV PATH ${PATH}:${HOME}/.cargo/bin

RUN chown -R ${USER_ID}:${USER_ID} ${HOME}/.cargo
RUN chmod 775 $HOME/.cargo

# Upgrade pip
RUN pip install --upgrade pip
RUN pip install virtualenv click

WORKDIR ${HOME}
RUN mkdir ${HOME}/bin
ADD ./bin ${HOME}/bin
ENV PATH $PATH:${HOME}/bin

ENV USER_ID ${USER_ID}
USER ${USER_ID}

RUN git config --global user.name "Generated Schema Creator"
RUN git config --global user.email "dataops+pipeline-schemas@mozilla.com"

ENTRYPOINT ["/app/bin/schema_generator.sh"]
