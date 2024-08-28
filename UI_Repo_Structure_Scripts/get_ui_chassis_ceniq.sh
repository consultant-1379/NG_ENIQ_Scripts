#!/bin/bash

function clone_chassis () {
  git_version=$(git --version)

  if [ ! -z "$git_version" ]; then
      printf "Cloning chassis\n"
      git clone https://gerrit.ericsson.se/a/OSS/ENIQ-CR-Parent/demo
      cd demo && git checkout mngmt-sys-ui && git archive HEAD | (cd ../ && tar xf -)
      cd .. && rm -rf demo
  else
      printf "git user.name not set, unable to proceed, please set up git and re-run."
      exit 1
  fi
}

## Git
function user_input_git_repo_path() {
  printf "If you have a git repo setup for your service please enter it here. If not press ENTER to proceed. \n"
  read -rp 'git-repo-path (e.g. OSS/ENIQ-CR-Parent/demo): ' gitRepoPath
  if [ ! -z "$gitRepoPath" ]; then
    sed -i "s+git-repo-path:.*+git-repo-path: $gitRepoPath+g" ruleset2.0.yaml
    sed -i "s+git-repo-path:.*+git-repo-path: $gitRepoPath+g" ruleset2.0.pra.yaml
  fi
}


function update_git_repo_path() {
  printf "\nUpdating git repo path\n"
  gitRepoPath=$(grep -s -o "29418/.*" .git/config | cut -f2- -d/)

  if [ ! -z "$gitRepoPath" ]; then
      read -rp "Please confirm if the following Git Repo Path is correct: $gitRepoPath (y/n): " gitContinueVar
      if [ "$gitContinueVar" == "y" ] || [ "$gitContinueVar" == "yes" ];
      then
          sed -i "s+git-repo-path:.*+git-repo-path: $gitRepoPath+g" ruleset2.0.yaml
      else
          user_input_git_repo_path
      fi
  else
      user_input_git_repo_path
  fi
  update_gerrit_url
}

function update_gerrit_url() {

  if [ ! -z "$gitRepoPath" ]; then
    gerritURL="\"https://gerrit.ericsson.se/a/$gitRepoPath\""
    printf "\nPlease enter the URL to browse the code in gerrit. (default: $gerritURL) \n"
    read -rp 'git-url: (e.g. https://gerrit.ericsson.se/a/OSS/ENIQ-CR-Parent/demo): ' gerritURL

    sed -i "s+gerrit-url:.*+gerrit-url: $gerritURL+g" common-properties.yaml
  fi
}

function update_git_username() {
    printf "\nUpdating git username in ruleset2.0.yaml\nEnter git user for CI pipeline. Press ENTER to use default.\n"
    read -rp "git-user (default: lciadm100): " gitUserVar
    if [ ! -z "$gitUserVar" ]; then
      sed -i "s+git-user:.*+git-user: $gitUserVar+g" ruleset2.0.yaml
      sed -i "s+git-user:.*+git-user: $gitUserVar+g" ruleset2.0.pra.yaml
    fi

}

function update_git_config() {
  update_git_repo_path
  update_git_username
}

# application.yaml
function update_application_yaml() {
  printf "\nUpdating application yaml\n"
  read -rp "Please provide a short description of your service: " descVar
  sed -i "s/^info.app.description:.*/info.app.description: $descVar/g" src/main/resources/application.yaml
}

# jenkinsfiles Team Name
function update_team_name_jenkinsfiles() {
  printf "\nUpdating team name in Jenkinsfiles\n"
  read -rp "Please provide the name of your team: " teamVar
  sed -i "s+TEAM_NAME =.*+TEAM_NAME = \"\$DEVELOPER_NAME - $teamVar\"+g" jenkinsfile/precodereview.Jenkinsfile
  sed -i "s+TEAM_NAME =.*+TEAM_NAME = \"\$DEVELOPER_NAME - $teamVar\"+g" jenkinsfile/publish.Jenkinsfile
}

# pom.xml
function user_input_pom_properties() {
  printf "Reading pom properties\n"
  ## ToDo possibly read group id and artifact id from the gitrepo path
  read -rp "Group Id (Should follow java package name rules https://maven.apache.org/guides/mini/guide-naming-conventions.html): " gidVar
  read -rp "Artifact Id (Should be name of the jar without version): " artifactIdVar
  read -rp "Name of service: " nameVar

  if [ ! -z "$nameVar" ]; then
    sed -i "s+:service_name:.*+:service_name: $nameVar+g" doc/parameters.adoc
  fi
}

# api-spec.yaml
function update_api_spec(){
  printf "%s\t%s \nThe recommended name for your api spec tile is: $nameVar-openapi.yaml.\n"
  read -rp "Please press ('y' to continue / 'n' to override): " override_api_spec_var
  if [ "$override_api_spec_var" == "y" ] || [ "$override_api_spec_var" == "yes" ]; then
        api_Spec_file_name="$nameVar-openapi.yaml";
  else
    read -rp "Enter new value for api spec file name (e.g. $nameVar-openapi.yaml): " api_Spec_file_name
  fi
  sed -i "s/Micro service chassis/$descVar/g" src/main/resources/v1/demo-openapi.yaml
  mv src/main/resources/v1/demo-openapi.yaml src/main/resources/v1/$api_Spec_file_name
}

# update java package
function update_java_package(){
  printf "%s\t%s \nThe recommended base package name name for your service is: $gidVar.\n"
  read -rp "Please press ('y' to continue / 'n' to override): " override_java_package_var
  if [ "$override_java_package_var" == "y" ] || [ "$override_java_package_var" == "yes" ]; then
        package_name="$gidVar";
  else
    read -rp "Enter new java package name (e.g. $gidVar): " package_name
  fi
  #create new package structure, move files and update package decleration.
  mkdir tempsrc
  mv src/main/java/com/ericsson/demo/service* tempsrc/
  mkdir -p src/main/java/${package_name//./\/}
  mv tempsrc/* src/main/java/${package_name//./\/}/

  mv src/test/java/com/ericsson/demo/service* tempsrc/
  mkdir -p src/test/java/${package_name//./\/}
  mv tempsrc/* src/test/java/${package_name//./\/}/

  find . -type d -empty -delete

  for f in $(find . -name *.java); do sed -i "s/com.ericsson.demo.service/$package_name/g" $f; done
}

function update_pom() {
  sed -i "s/<groupId>com.ericsson.demo.service<\/groupId>/<groupId>$gidVar<\/groupId>/g" pom.xml
  sed -i "s/<artifactId>demo<\/artifactId>/<artifactId>$artifactIdVar<\/artifactId>/g" pom.xml
  sed -i "s/<name>demo<\/name>/<name>$nameVar<\/name>/g" pom.xml
  sed -i "s/demo-openapi.yaml/$api_Spec_file_name/g" pom.xml
  sed -i "s/com.ericsson.demo.service.api/$package_name.api/g" pom.xml
}

## DockerImage
function update_docker_properties() {
  printf "\nUpdating docker properties in ruleset2.0.yaml.\n"
  read -rp "Docker image name (e.g. eric-oss-eniq-test. See https://confluence.lmera.ericsson.se/display/AA/Container+image+design+rules.): " dockerImgNameVar
  sed -i "s/docker-image-name:.*/docker-image-name: $dockerImgNameVar/g" common-properties.yaml

  read -rp "Docker Registry (Please press ENTER for default = armdocker.rnd.ericsson.se): " dockerReg
  if [ ! -z "$dockerReg" ]; then
    sed -i "s+image-registry:.*+image-registry: $dockerReg+g" ruleset2.0.yaml
  fi

  read -rp "Docker repo prefix (e.g. proj-eniq. Press ENTER for no prefix): " prefix
  if [ ! -z "$prefix" ]; then
    imgDevRepoPathVar="$prefix/proj-$dockerImgNameVar-dev"
    imgRelRepoPathVar="$prefix/proj-$dockerImgNameVar-release"
  else
    imgDevRepoPathVar="proj-$dockerImgNameVar-dev"
    imgRelRepoPathVar="proj-$dockerImgNameVar-release"
  fi

  printf "\nThe following DOCKER repo paths will be set in the ruleset2.0.yaml: \n"
  printf "%s\t%s image-dev-repopath: $imgDevRepoPathVar \n"
  printf "%s\t%s image-release-repopath: $imgRelRepoPathVar \n"

  read -rp "Please confirm ('y' to continue / 'n' to setup later): " dockerContinueVar
  if [ "$dockerContinueVar" == "y" ] || [ "$dockerContinueVar" == "yes" ]; then
    sed -i "s+image-dev-repopath:.*+image-dev-repopath: $imgDevRepoPathVar+g" ruleset2.0.yaml
    sed -i "s+image-release-repopath:.*+image-release-repopath: $imgRelRepoPathVar+g" ruleset2.0.yaml
  else
    printf "Not setting any docker repo paths in ruleset2.0.yaml, you must update these manually once the docker repo has been setup."
  fi

}

## Helm
function update_helm_properties() {
  printf "\nUpdating helm properties in ruleset2.0.yaml.\n"
  read -rp "helm-chart-name (e.g. demo. See https://confluence.lmera.ericsson.se/display/AA/Helm+Chart+Design+Rules+and+Guidelines.): " helmChartNameVar
  sed -i "s/helm-chart-name:.*/helm-chart-name: $helmChartNameVar/g" common-properties.yaml
  mv charts/demo/ charts/$helmChartNameVar/

  helmChartRelRepoPathVar="proj-eniq-drop-helm"

  mv client/apps/demo client/apps/$helmChartNameVar/

  printf "\nThe following HELM repo paths will be set in the ruleset2.0.yaml: \n"
  printf "%s\t%s helm-chart-release-repopath: $helmChartRelRepoPathVar \n"

  read -rp "Please confirm ('y' to continue / 'n' to setup later): " helmContinueVar

  if [ "$helmContinueVar" == "y" ] || [ "$helmContinueVar" == "yes" ]; then
    sed -i "s+helm-chart-release-repopath:.*+helm-chart-release-repopath: $helmChartRelRepoPathVar+g" ruleset2.0.yaml
  else
    printf "Not setting any helm repo paths in ruleset2.0.yaml, you must update these manually once the helm repo has been setup."
  fi

}

## Jar File Name
function update_jar_file() {
  printf "\nUpdating jar file name in ruleset2.0.yaml\n"
  jarFileName="$artifactIdVar-1.0.0-SNAPSHOT.jar"
  sed -i "s/jar-file-name:.*/jar-file-name: $jarFileName/g" ruleset2.0.yaml
}

## Update K8_NAMESPACE
function update_k8_namespace() {
    k8NamespaceVar=$K8_NAMESPACE
    if [ -z "$k8NamespaceVar" ]; then
      k8NamespaceVar="default-namespace"
    fi
    printf "%s\n%s %s %s" "Updating K8_NAMESPACE in ruleset2.0.yaml" "Press ENTER to set $k8NamespaceVar" "or enter new value to change"
    read -rp "K8_NAMESPACE: " k8NamespaceVar
    if [ ! -z "$k8NamespaceVar" ]; then
      sed -i "s+K8_NAMESPACE (default=default-namespace).*+K8_NAMESPACE (default=$k8NamespaceVar)+g" ruleset2.0.yaml
    fi

}

# ruleset2.0.yaml
function update_ruleset_yaml() {
   update_docker_properties
   update_helm_properties
   update_k8_namespace
}

# Adding bob
function bob_add() {
    git submodule add ../../../adp-cicd/bob bob
}

clone_chassis
update_git_config
update_team_name_jenkinsfiles
update_ruleset_yaml
bob_add
#rm ./get_chassis_ceniq.sh
