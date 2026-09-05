#include "../src/host_command_lane_v30.h"
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    if(kCC_AIAssist!=102 || kCC_RetakeTarget!=106 || kCC_MidiAuthorityLock!=109 || kCC_LayoutMode!=117 || kCC_Humanize!=119) return 2;
    if(kHostCommandCCLast-kHostCommandCCFirst+1!=18) return 3;
    std::cout << "SONICRAFT v3.0 Host Command Lane native contract OK: CC " << kHostCommandCCFirst << ".." << kHostCommandCCLast << "\n";
    return 0;
}
