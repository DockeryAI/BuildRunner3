#!/bin/bash
# BuildRunner 3.0 - Shell Aliases
# Enforces BR3 checks on deployment commands
#
# Usage: source .buildrunner/scripts/br3-aliases.sh

# Find project root (where .buildrunner exists)
if [ -d ".buildrunner" ]; then
    BR3_PROJECT_ROOT="$(pwd)"
elif [ -d "../.buildrunner" ]; then
    BR3_PROJECT_ROOT="$(cd .. && pwd)"
elif [ -d "../../.buildrunner" ]; then
    BR3_PROJECT_ROOT="$(cd ../.. && pwd)"
else
    # Search upwards for .buildrunner
    BR3_PROJECT_ROOT="$(pwd)"
    while [ "$BR3_PROJECT_ROOT" != "/" ]; do
        if [ -d "$BR3_PROJECT_ROOT/.buildrunner" ]; then
            break
        fi
        BR3_PROJECT_ROOT="$(dirname "$BR3_PROJECT_ROOT")"
    done
fi

# Only set up aliases if we found .buildrunner
if [ -d "$BR3_PROJECT_ROOT/.buildrunner" ]; then
    export BR3_PROJECT_ROOT

    # Deployment wrapper path
    BR3_DEPLOY_WRAPPER="$BR3_PROJECT_ROOT/.buildrunner/scripts/deploy-wrapper.sh"

    # If wrapper exists, create deployment aliases
    if [ -f "$BR3_DEPLOY_WRAPPER" ]; then
        # Supabase functions deploy
        alias supabase-deploy="$BR3_DEPLOY_WRAPPER supabase functions deploy"

        # Netlify deploy
        alias netlify-deploy="$BR3_DEPLOY_WRAPPER netlify deploy"

        # Vercel deploy
        alias vercel-deploy="$BR3_DEPLOY_WRAPPER vercel deploy"

        # Docker deploy
        alias docker-deploy="$BR3_DEPLOY_WRAPPER docker push"

        # Generic deploy command
        alias br-deploy="$BR3_DEPLOY_WRAPPER"

        # Show message on first load
        if [ -z "$BR3_ALIASES_LOADED" ]; then
            echo "✅ BR3 deployment enforcement active"
            echo "   • Use 'supabase-deploy' instead of 'supabase functions deploy'"
            echo "   • Or prefix any deploy command with 'br-deploy'"
            export BR3_ALIASES_LOADED=1
        fi
    fi
fi
