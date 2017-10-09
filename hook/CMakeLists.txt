cmake_minimum_required( VERSION 2.8 )

if( CMAKE_SIZEOF_VOID_P EQUAL 8 )
    add_library( hook64 SHARED hook.c hook64.def )
    install( TARGETS hook64 DESTINATION ${PROJECT_SOURCE_DIR} )
else( CMAKE_SIZEOF_VOID_P EQUAL 8 )
    add_library( hook32 SHARED hook.c hook32.def )
    install( TARGETS hook32 DESTINATION ${PROJECT_SOURCE_DIR} )
endif( CMAKE_SIZEOF_VOID_P EQUAL 8 )
